"""
SemanticMemory - Unified interface for semantic search across vector store and knowledge graph
"""

import os
import json
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import threading

from core.memory.vector_store import (
    VectorStoreBase, VectorDocument, get_vector_store, create_embedding
)
from core.memory.knowledge_graph import KnowledgeGraph, Entity, Relation, extract_with_llm


@dataclass
class MemorySearchResult:
    """Result from semantic memory search."""
    content: str
    score: float
    metadata: Dict[str, Any]
    source: str  # "vector" or "graph"
    timestamp: str
    entities: List[Entity] = None
    relations: List[Relation] = None


class SemanticMemory:
    """Unified semantic memory combining vector search and knowledge graph."""
    
    def __init__(
        self,
        vector_store: Optional[VectorStoreBase] = None,
        knowledge_graph: Optional[KnowledgeGraph] = None,
        embedding_provider: str = "mock",
        llm_provider=None,
        db_path: str = "indus.db"
    ):
        self.vector_store = vector_store or get_vector_store(provider="mock")
        self.knowledge_graph = knowledge_graph or KnowledgeGraph(
            db_path=db_path.replace(".db", "_kg.db")
        )
        self.embedding_provider = embedding_provider
        self.llm_provider = llm_provider
        self.db_path = db_path
        self._lock = threading.Lock()
        
        # Initialize SQLite for temporal indexing
        self._init_temporal_index()
    
    def _init_temporal_index(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS temporal_index (
                id TEXT PRIMARY KEY,
                content_hash TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                date_key TEXT NOT NULL,  -- YYYY-MM-DD
                week_key TEXT NOT NULL,  -- YYYY-WW
                month_key TEXT NOT NULL, -- YYYY-MM
                year_key TEXT NOT NULL,  -- YYYY
                metadata TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_temporal_date ON temporal_index(date_key)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_temporal_week ON temporal_index(week_key)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_temporal_month ON temporal_index(month_key)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_temporal_year ON temporal_index(year_key)")
        conn.commit()
        conn.close()
    
    def add_conversation(
        self,
        user_message: str,
        assistant_response: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """Add conversation turn to semantic memory."""
        
        timestamp = datetime.now().isoformat()
        date_key = datetime.now().strftime("%Y-%m-%d")
        week_key = datetime.now().strftime("%Y-W%U")
        month_key = datetime.now().strftime("%Y-%m")
        year_key = datetime.now().strftime("%Y")
        
        meta = metadata or {}
        meta.update({
            "type": "conversation",
            "user_message": user_message,
            "assistant_response": assistant_response
        })
        
        # Create combined content for embedding
        combined_content = f"User: {user_message}\nAssistant: {assistant_response}"
        
        # Create embedding
        embedding = create_embedding(combined_content, provider=self.embedding_provider)
        
        # Store in vector store
        doc = VectorDocument(
            id="",
            content=combined_content,
            metadata=meta,
            embedding=embedding,
            timestamp=timestamp
        )
        vector_ids = self.vector_store.add([doc])
        
        # Extract entities and relations with LLM
        if self.llm_provider:
            entities, relations = extract_with_llm(combined_content, self.llm_provider)
            
            # Add to knowledge graph
            entity_ids = {}
            for entity in entities:
                eid = self.knowledge_graph.add_entity(entity)
                entity_ids[entity.name] = eid
            
            for relation in relations:
                source_id = entity_ids.get(relation.source_id)
                target_id = entity_ids.get(relation.target_id)
                if source_id and target_id:
                    relation.source_id = source_id
                    relation.target_id = target_id
                    self.knowledge_graph.add_relation(relation)
        
        # Index temporally
        self._index_temporally(
            vector_ids[0], combined_content, timestamp,
            date_key, week_key, month_key, year_key, meta
        )
        
        return vector_ids
    
    def _index_temporally(
        self, doc_id: str, content: str, timestamp: str,
        date_key: str, week_key: str, month_key: str, year_key: str, metadata: Dict
    ):
        import hashlib
        content_hash = hashlib.md5(content.encode()).hexdigest()
        
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT OR REPLACE INTO temporal_index 
            (id, content_hash, timestamp, date_key, week_key, month_key, year_key, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (doc_id, content_hash, timestamp, date_key, week_key, month_key, year_key, json.dumps(metadata)))
        conn.commit()
        conn.close()
    
    def search(
        self,
        query: str,
        limit: int = 10,
        filter_metadata: Optional[Dict[str, Any]] = None,
        include_graph: bool = True
    ) -> List[MemorySearchResult]:
        """Semantic search across vector store and knowledge graph."""
        
        # Create query embedding
        query_embedding = create_embedding(query, provider=self.embedding_provider)
        
        # Vector search
        vector_results = self.vector_store.search(
            query_embedding=query_embedding,
            limit=limit,
            filter_metadata=filter_metadata
        )
        
        results = []
        for doc in vector_results:
            results.append(MemorySearchResult(
                content=doc.content,
                score=1.0,  # Would need actual similarity score
                metadata=doc.metadata,
                source="vector",
                timestamp=doc.timestamp
            ))
        
        # Graph search - find relevant entities
        if include_graph and self.llm_provider:
            entities = self.knowledge_graph.search_entities(query, limit=5)
            for entity in entities:
                relations = self.knowledge_graph.get_relations(entity.id)
                graph_content = f"Entity: {entity.name} ({entity.type})\n"
                graph_content += f"Properties: {json.dumps(entity.properties)}\n"
                if relations:
                    graph_content += "Relations:\n"
                    for rel, target in relations:
                        graph_content += f"  - {rel.relation_type} -> {target.name} ({target.type})\n"
                
                results.append(MemorySearchResult(
                    content=graph_content,
                    score=0.8,
                    metadata={"entity_id": entity.id, "entity_type": entity.type},
                    source="graph",
                    timestamp=entity.last_seen,
                    entities=[entity],
                    relations=[r for r, _ in relations]
                ))
        
        # Sort by score
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:limit]
    
    def recall_date(self, date_str: str, limit: int = 20) -> List[MemorySearchResult]:
        """Recall memories from a specific date (YYYY-MM-DD)."""
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            date_key = date_obj.strftime("%Y-%m-%d")
        except ValueError:
            return []
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM temporal_index WHERE date_key = ? ORDER BY timestamp DESC LIMIT ?",
            (date_key, limit)
        ).fetchall()
        conn.close()
        
        results = []
        for row in rows:
            metadata = json.loads(row["metadata"])
            doc = self.vector_store.get(row["id"])
            if doc:
                results.append(MemorySearchResult(
                    content=doc.content,
                    score=1.0,
                    metadata=metadata,
                    source="temporal",
                    timestamp=doc.timestamp
                ))
        
        return results
    
    def recall_week(self, year_week: str, limit: int = 30) -> List[MemorySearchResult]:
        """Recall memories from a specific week (YYYY-WW)."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM temporal_index WHERE week_key = ? ORDER BY timestamp DESC LIMIT ?",
            (year_week, limit)
        ).fetchall()
        conn.close()
        
        return self._temporal_rows_to_results(rows)
    
    def recall_month(self, year_month: str, limit: int = 50) -> List[MemorySearchResult]:
        """Recall memories from a specific month (YYYY-MM)."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM temporal_index WHERE month_key = ? ORDER BY timestamp DESC LIMIT ?",
            (year_month, limit)
        ).fetchall()
        conn.close()
        
        return self._temporal_rows_to_results(rows)
    
    def _temporal_rows_to_results(self, rows) -> List[MemorySearchResult]:
        results = []
        for row in rows:
            metadata = json.loads(row["metadata"])
            doc = self.vector_store.get(row["id"])
            if doc:
                results.append(MemorySearchResult(
                    content=doc.content,
                    score=1.0,
                    metadata=metadata,
                    source="temporal",
                    timestamp=doc.timestamp
                ))
        return results
    
    def get_summary(
        self,
        period: str = "week",  # day, week, month, year
        reference_date: Optional[str] = None
    ) -> str:
        """Generate summary for a time period."""
        
        if reference_date:
            ref = datetime.strptime(reference_date, "%Y-%m-%d")
        else:
            ref = datetime.now()
        
        if period == "day":
            date_key = ref.strftime("%Y-%m-%d")
            memories = self.recall_date(date_key, limit=50)
        elif period == "week":
            week_key = ref.strftime("%Y-W%U")
            memories = self.recall_week(week_key, limit=100)
        elif period == "month":
            month_key = ref.strftime("%Y-%m")
            memories = self.recall_month(month_key, limit=200)
        else:
            year_key = ref.strftime("%Y")
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM temporal_index WHERE year_key = ? ORDER BY timestamp DESC LIMIT ?",
                (year_key, 500)
            ).fetchall()
            conn.close()
            memories = self._temporal_rows_to_results(rows)
        
        if not memories:
            return f"No memories found for {period} ending {ref.strftime('%Y-%m-%d')}"
        
        # Use LLM to generate summary
        if self.llm_provider:
            combined = "\n---\n".join([m.content for m in memories[:30]])
            prompt = f"""Summarize the following conversation memories from {period} ending {ref.strftime('%Y-%m-%d')}:

{combined}

Provide a concise summary covering key topics, entities mentioned, and notable events."""
            
            try:
                summary = self.llm_provider.chat([
                    {"role": "system", "content": "You are a memory summarizer. Create concise, informative summaries."},
                    {"role": "user", "content": prompt}
                ])
                return summary
            except Exception:
                pass
        
        # Fallback: simple stats
        topics = set()
        entities_mentioned = set()
        for m in memories:
            meta = m.metadata
            if meta.get("type") == "conversation":
                topics.add("conversation")
            # Could extract more from metadata
        
        return f"{period.capitalize()} summary: {len(memories)} memories. Topics: {', '.join(topics) or 'general'}"
    
    def learn_fact(self, fact: str, category: str = "general", confidence: float = 1.0) -> str:
        """Explicitly store a fact in knowledge graph."""
        
        entity = Entity(
            id="",
            name=fact[:100],
            type="fact",
            properties={"content": fact, "category": category},
            confidence=confidence
        )
        
        entity_id = self.knowledge_graph.add_entity(entity)
        
        # Also store in vector store for semantic search
        embedding = create_embedding(fact, provider=self.embedding_provider)
        doc = VectorDocument(
            id="",
            content=f"Fact: {fact}",
            metadata={"type": "fact", "category": category, "confidence": confidence},
            embedding=embedding,
            timestamp=datetime.now().isoformat()
        )
        self.vector_store.add([doc])
        
        return f"Learned fact: {fact}"
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "vector_store_count": self.vector_store.count(),
            "knowledge_graph": self.knowledge_graph.get_stats()
        }


# Global instance
_semantic_memory: Optional[SemanticMemory] = None


def get_semantic_memory(
    vector_store_provider: str = "mock",
    embedding_provider: str = "mock",
    llm_provider=None,
    **kwargs
) -> SemanticMemory:
    global _semantic_memory
    if _semantic_memory is None:
        vs = get_vector_store(provider=vector_store_provider, **kwargs)
        kg = KnowledgeGraph(db_path=kwargs.get("db_path", "indus.db").replace(".db", "_kg.db"))
        _semantic_memory = SemanticMemory(
            vector_store=vs,
            knowledge_graph=kg,
            embedding_provider=embedding_provider,
            llm_provider=llm_provider,
            db_path=kwargs.get("db_path", "indus.db")
        )
    return _semantic_memory


import sqlite3