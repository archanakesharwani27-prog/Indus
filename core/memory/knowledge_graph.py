"""
KnowledgeGraph - Entity and relation extraction + storage (NetworkX + SQLite)
"""

import os
import json
import sqlite3
import uuid
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from collections import defaultdict
import networkx as nx


@dataclass
class Entity:
    """Entity in the knowledge graph."""
    id: str
    name: str
    type: str  # person, place, organization, concept, event, date, etc.
    properties: Dict[str, Any]
    confidence: float = 1.0
    first_seen: str = ""
    last_seen: str = ""
    mention_count: int = 1
    
    def __post_init__(self):
        if not self.first_seen:
            self.first_seen = datetime.now().isoformat()
        if not self.last_seen:
            self.last_seen = datetime.now().isoformat()


@dataclass
class Relation:
    """Relation between entities."""
    id: str
    source_id: str
    target_id: str
    relation_type: str  # works_at, located_in, knows, mentioned_with, etc.
    properties: Dict[str, Any]
    confidence: float = 1.0
    first_seen: str = ""
    last_seen: str = ""
    mention_count: int = 1
    
    def __post_init__(self):
        if not self.first_seen:
            self.first_seen = datetime.now().isoformat()
        if not self.last_seen:
            self.last_seen = datetime.now().isoformat()


class KnowledgeGraph:
    """Knowledge graph with NetworkX for traversal + SQLite for persistence."""
    
    def __init__(self, db_path: str = "indus_kg.db"):
        self.db_path = db_path
        self._graph = nx.MultiDiGraph()
        self._init_db()
        self._load_from_db()
    
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS entities (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                properties TEXT NOT NULL,
                confidence REAL DEFAULT 1.0,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                mention_count INTEGER DEFAULT 1
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS relations (
                id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                properties TEXT NOT NULL,
                confidence REAL DEFAULT 1.0,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                mention_count INTEGER DEFAULT 1,
                FOREIGN KEY (source_id) REFERENCES entities(id),
                FOREIGN KEY (target_id) REFERENCES entities(id)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_relations_source ON relations(source_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_relations_target ON relations(target_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_relations_type ON relations(relation_type)")
        conn.commit()
        conn.close()
    
    def _load_from_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        for row in conn.execute("SELECT * FROM entities"):
            entity = Entity(
                id=row["id"],
                name=row["name"],
                type=row["type"],
                properties=json.loads(row["properties"]),
                confidence=row["confidence"],
                first_seen=row["first_seen"],
                last_seen=row["last_seen"],
                mention_count=row["mention_count"]
            )
            self._graph.add_node(entity.id, **asdict(entity))
        
        for row in conn.execute("SELECT * FROM relations"):
            relation = Relation(
                id=row["id"],
                source_id=row["source_id"],
                target_id=row["target_id"],
                relation_type=row["relation_type"],
                properties=json.loads(row["properties"]),
                confidence=row["confidence"],
                first_seen=row["first_seen"],
                last_seen=row["last_seen"],
                mention_count=row["mention_count"]
            )
            self._graph.add_edge(
                relation.source_id,
                relation.target_id,
                key=relation.id,
                **asdict(relation)
            )
        
        conn.close()
    
    def add_entity(self, entity: Entity) -> str:
        """Add or update entity."""
        existing = self._find_entity_by_name(entity.name, entity.type)
        
        if existing:
            existing.mention_count += 1
            existing.last_seen = datetime.now().isoformat()
            existing.confidence = min(1.0, existing.confidence + 0.05)
            existing.properties.update(entity.properties)
            self._update_entity_db(existing)
            self._graph.nodes[existing.id].update(asdict(existing))
            return existing.id
        
        if not entity.id:
            entity.id = str(uuid.uuid4())
        
        self._graph.add_node(entity.id, **asdict(entity))
        self._save_entity_db(entity)
        return entity.id
    
    def _find_entity_by_name(self, name: str, type: str) -> Optional[Entity]:
        for node_id, data in self._graph.nodes(data=True):
            if data.get("name", "").lower() == name.lower() and data.get("type") == type:
                return Entity(**data)
        return None
    
    def _save_entity_db(self, entity: Entity):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT OR REPLACE INTO entities (id, name, type, properties, confidence, first_seen, last_seen, mention_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entity.id, entity.name, entity.type,
            json.dumps(entity.properties), entity.confidence,
            entity.first_seen, entity.last_seen, entity.mention_count
        ))
        conn.commit()
        conn.close()
    
    def _update_entity_db(self, entity: Entity):
        self._save_entity_db(entity)
    
    def add_relation(self, relation: Relation) -> str:
        """Add or update relation."""
        existing = self._find_relation(
            relation.source_id, relation.target_id, relation.relation_type
        )
        
        if existing:
            existing.mention_count += 1
            existing.last_seen = datetime.now().isoformat()
            existing.confidence = min(1.0, existing.confidence + 0.05)
            existing.properties.update(relation.properties)
            self._update_relation_db(existing)
            edge_data = self._graph.get_edge_data(relation.source_id, relation.target_id, key=existing.id)
            if edge_data:
                edge_data.update(asdict(existing))
            return existing.id
        
        if not relation.id:
            relation.id = str(uuid.uuid4())
        
        self._graph.add_edge(
            relation.source_id,
            relation.target_id,
            key=relation.id,
            **asdict(relation)
        )
        self._save_relation_db(relation)
        return relation.id
    
    def _find_relation(self, source_id: str, target_id: str, relation_type: str) -> Optional[Relation]:
        if self._graph.has_edge(source_id, target_id):
            for key, data in self._graph[source_id][target_id].items():
                if data.get("relation_type") == relation_type:
                    return Relation(**data)
        return None
    
    def _save_relation_db(self, relation: Relation):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT OR REPLACE INTO relations (id, source_id, target_id, relation_type, properties, confidence, first_seen, last_seen, mention_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            relation.id, relation.source_id, relation.target_id,
            relation.relation_type, json.dumps(relation.properties),
            relation.confidence, relation.first_seen, relation.last_seen, relation.mention_count
        ))
        conn.commit()
        conn.close()
    
    def _update_relation_db(self, relation: Relation):
        self._save_relation_db(relation)
    
    def get_entity(self, entity_id: str) -> Optional[Entity]:
        if entity_id in self._graph:
            data = self._graph.nodes[entity_id]
            return Entity(**data)
        return None
    
    def get_entities_by_type(self, type: str) -> List[Entity]:
        return [Entity(**data) for _, data in self._graph.nodes(data=True) if data.get("type") == type]
    
    def search_entities(self, query: str, limit: int = 10) -> List[Entity]:
        query_lower = query.lower()
        results = []
        for _, data in self._graph.nodes(data=True):
            if query_lower in data.get("name", "").lower():
                results.append(Entity(**data))
                if len(results) >= limit:
                    break
        return results
    
    def get_relations(
        self,
        entity_id: str,
        relation_type: Optional[str] = None,
        direction: str = "both"
    ) -> List[Tuple[Relation, Entity]]:
        results = []
        
        if direction in ("out", "both"):
            for _, target, key, data in self._graph.out_edges(entity_id, data=True, keys=True):
                if relation_type is None or data.get("relation_type") == relation_type:
                    relation = Relation(**data)
                    target_entity = self.get_entity(target)
                    if target_entity:
                        results.append((relation, target_entity))
        
        if direction in ("in", "both"):
            for source, _, key, data in self._graph.in_edges(entity_id, data=True, keys=True):
                if relation_type is None or data.get("relation_type") == relation_type:
                    relation = Relation(**data)
                    source_entity = self.get_entity(source)
                    if source_entity:
                        results.append((relation, source_entity))
        
        return results
    
    def find_path(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 3
    ) -> Optional[List[Tuple[Entity, Relation, Entity]]]:
        try:
            paths = list(nx.all_simple_paths(self._graph, source_id, target_id, cutoff=max_depth))
            if not paths:
                return None
            
            path = paths[0]
            result = []
            for i in range(len(path) - 1):
                source = self.get_entity(path[i])
                target = self.get_entity(path[i + 1])
                edge_data = self._graph.get_edge_data(path[i], path[i + 1])
                if edge_data:
                    for key, data in edge_data.items():
                        relation = Relation(**data)
                        result.append((source, relation, target))
                        break
            return result
        except nx.NetworkXNoPath:
            return None
    
    def get_subgraph(self, entity_ids: List[str], depth: int = 1) -> nx.MultiDiGraph:
        nodes = set(entity_ids)
        for eid in entity_ids:
            nodes.update(nx.single_source_shortest_path_length(self._graph, eid, cutoff=depth).keys())
            nodes.update(nx.single_source_shortest_path_length(self._graph.reverse(), eid, cutoff=depth).keys())
        return self._graph.subgraph(nodes).copy()
    
    def get_stats(self) -> Dict[str, Any]:
        entity_types = defaultdict(int)
        relation_types = defaultdict(int)
        
        for _, data in self._graph.nodes(data=True):
            entity_types[data.get("type", "unknown")] += 1
        
        for _, _, data in self._graph.edges(data=True):
            relation_types[data.get("relation_type", "unknown")] += 1
        
        return {
            "total_entities": self._graph.number_of_nodes(),
            "total_relations": self._graph.number_of_edges(),
            "entity_types": dict(entity_types),
            "relation_types": dict(relation_types)
        }
    
    def export_json(self) -> Dict[str, Any]:
        entities = [dict(data) for _, data in self._graph.nodes(data=True)]
        relations = []
        for source, target, data in self._graph.edges(data=True):
            rel = dict(data)
            rel["source"] = source
            rel["target"] = target
            relations.append(rel)
        return {"entities": entities, "relations": relations}


def extract_entities_and_relations(
    text: str,
    llm_provider=None
) -> Tuple[List[Entity], List[Relation]]:
    """Extract entities and relations from text using LLM."""
    
    if llm_provider:
        # Use LLM-based extraction (to be implemented with function calling)
        pass
    
    # Fallback: simple pattern-based extraction
    entities = []
    relations = []
    
    # This is a placeholder - real implementation would use LLM
    # with function calling to extract structured entities/relations
    
    return entities, relations


def extract_with_llm(text: str, llm_provider) -> Tuple[List[Entity], List[Relation]]:
    """Extract entities and relations using LLM function calling."""
    
    system_prompt = """You are an entity and relation extractor. Analyze the text and extract:
1. Entities: people, places, organizations, concepts, events, dates, etc.
2. Relations: connections between entities (works_at, located_in, knows, mentioned_with, etc.)

Return ONLY valid JSON in this format:
{
  "entities": [
    {"name": "Ansh", "type": "person", "properties": {"role": "user"}, "confidence": 0.9}
  ],
  "relations": [
    {"source": "Ansh", "target": "Indus", "relation_type": "uses", "properties": {}, "confidence": 0.8}
  ]
}"""
    
    try:
        response = llm_provider.chat([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ])
        
        import json
        parsed = json.loads(response)
        
        entities = []
        for e in parsed.get("entities", []):
            entities.append(Entity(
                id="",
                name=e["name"],
                type=e["type"],
                properties=e.get("properties", {}),
                confidence=e.get("confidence", 0.8)
            ))
        
        relations = []
        for r in parsed.get("relations", []):
            relations.append(Relation(
                id="",
                source_id=r["source"],
                target_id=r["target"],
                relation_type=r["relation_type"],
                properties=r.get("properties", {}),
                confidence=r.get("confidence", 0.8)
            ))
        
        return entities, relations
    except Exception:
        return [], []