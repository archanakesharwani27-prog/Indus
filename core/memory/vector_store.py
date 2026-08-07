"""
VectorStore - Semantic search using embeddings (Qdrant or ChromaDB)
"""

import os
import uuid
import json
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class VectorDocument:
    """Document stored in vector database."""
    id: str
    content: str
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class VectorStoreBase(ABC):
    """Abstract base class for vector stores."""
    
    @abstractmethod
    def add(self, documents: List[VectorDocument]) -> List[str]:
        """Add documents to store. Returns list of IDs."""
        pass
    
    @abstractmethod
    def search(
        self, 
        query_embedding: List[float], 
        limit: int = 10,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[VectorDocument]:
        """Search for similar documents."""
        pass
    
    @abstractmethod
    def delete(self, ids: List[str]) -> bool:
        """Delete documents by IDs."""
        pass
    
    @abstractmethod
    def get(self, id: str) -> Optional[VectorDocument]:
        """Get document by ID."""
        pass
    
    @abstractmethod
    def count(self) -> int:
        """Get total document count."""
        pass


class QdrantVectorStore(VectorStoreBase):
    """Qdrant vector database implementation."""
    
    def __init__(
        self,
        collection_name: str = "indus_memory",
        host: str = "localhost",
        port: int = 6333,
        embedding_dim: int = 1536
    ):
        self.collection_name = collection_name
        self.embedding_dim = embedding_dim
        
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
            self._client = QdrantClient(host=host, port=port)
            self._models = __import__('qdrant_client.models', fromlist=['Distance', 'VectorParams', 'PointStruct', 'Filter', 'FieldCondition', 'MatchValue'])
            self._ensure_collection()
        except ImportError:
            raise ImportError("qdrant-client not installed. pip install qdrant-client")
    
    def _ensure_collection(self):
        """Create collection if it doesn't exist."""
        try:
            self._client.get_collection(self.collection_name)
        except Exception:
            self._client.create_collection(
                collection_name=self.collection_name,
                vectors_config=self._models.VectorParams(
                    size=self.embedding_dim,
                    distance=self._models.Distance.COSINE
                )
            )
    
    def add(self, documents: List[VectorDocument]) -> List[str]:
        points = []
        ids = []
        
        for doc in documents:
            doc_id = doc.id or str(uuid.uuid4())
            ids.append(doc_id)
            
            point = self._models.PointStruct(
                id=doc_id,
                vector=doc.embedding,
                payload={
                    "content": doc.content,
                    "metadata": doc.metadata,
                    "timestamp": doc.timestamp
                }
            )
            points.append(point)
        
        self._client.upsert(collection_name=self.collection_name, points=points)
        return ids
    
    def search(
        self,
        query_embedding: List[float],
        limit: int = 10,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[VectorDocument]:
        query_filter = None
        if filter_metadata:
            conditions = []
            for key, value in filter_metadata.items():
                conditions.append(
                    self._models.FieldCondition(
                        key=f"metadata.{key}",
                        match=self._models.MatchValue(value=value)
                    )
                )
            if conditions:
                query_filter = self._models.Filter(must=conditions)
        
        results = self._client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=limit,
            query_filter=query_filter,
            with_payload=True,
            with_vectors=True
        )
        
        documents = []
        for result in results:
            payload = result.payload
            doc = VectorDocument(
                id=str(result.id),
                content=payload.get("content", ""),
                metadata=payload.get("metadata", {}),
                embedding=result.vector,
                timestamp=payload.get("timestamp", "")
            )
            documents.append(doc)
        
        return documents
    
    def delete(self, ids: List[str]) -> bool:
        try:
            self._client.delete(
                collection_name=self.collection_name,
                points_selector=self._models.PointIdsList(points=ids)
            )
            return True
        except Exception:
            return False
    
    def get(self, id: str) -> Optional[VectorDocument]:
        results = self._client.retrieve(
            collection_name=self.collection_name,
            ids=[id],
            with_payload=True,
            with_vectors=True
        )
        
        if results:
            result = results[0]
            payload = result.payload
            return VectorDocument(
                id=str(result.id),
                content=payload.get("content", ""),
                metadata=payload.get("metadata", {}),
                embedding=result.vector,
                timestamp=payload.get("timestamp", "")
            )
        return None
    
    def count(self) -> int:
        info = self._client.get_collection(self.collection_name)
        return info.points_count


class ChromaVectorStore(VectorStoreBase):
    """ChromaDB vector database implementation."""
    
    def __init__(
        self,
        collection_name: str = "indus_memory",
        persist_directory: str = "./chroma_db",
        embedding_dim: int = 1536
    ):
        self.collection_name = collection_name
        self.embedding_dim = embedding_dim
        
        try:
            import chromadb
            from chromadb.config import Settings
            self._client = chromadb.PersistentClient(
                path=persist_directory,
                settings=Settings(anonymized_telemetry=False)
            )
            self._collection = self._client.get_or_create_collection(name=collection_name)
        except ImportError:
            raise ImportError("chromadb not installed. pip install chromadb")
    
    def add(self, documents: List[VectorDocument]) -> List[str]:
        ids = []
        contents = []
        metadatas = []
        embeddings = []
        
        for doc in documents:
            doc_id = doc.id or str(uuid.uuid4())
            ids.append(doc_id)
            contents.append(doc.content)
            metadatas.append({**doc.metadata, "timestamp": doc.timestamp})
            embeddings.append(doc.embedding)
        
        self._collection.add(
            ids=ids,
            documents=contents,
            metadatas=metadatas,
            embeddings=embeddings
        )
        return ids
    
    def search(
        self,
        query_embedding: List[float],
        limit: int = 10,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[VectorDocument]:
        where = filter_metadata if filter_metadata else None
        
        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=limit,
            where=where,
            include=["documents", "metadatas", "embeddings"]
        )
        
        documents = []
        if results["ids"] and results["ids"][0]:
            for i in range(len(results["ids"][0])):
                metadata = results["metadatas"][0][i]
                timestamp = metadata.pop("timestamp", "")
                
                doc = VectorDocument(
                    id=results["ids"][0][i],
                    content=results["documents"][0][i],
                    metadata=metadata,
                    embedding=results["embeddings"][0][i] if results["embeddings"] else None,
                    timestamp=timestamp
                )
                documents.append(doc)
        
        return documents
    
    def delete(self, ids: List[str]) -> bool:
        try:
            self._collection.delete(ids=ids)
            return True
        except Exception:
            return False
    
    def get(self, id: str) -> Optional[VectorDocument]:
        results = self._collection.get(ids=[id], include=["documents", "metadatas", "embeddings"])
        
        if results["ids"]:
            metadata = results["metadatas"][0]
            timestamp = metadata.pop("timestamp", "")
            
            return VectorDocument(
                id=results["ids"][0],
                content=results["documents"][0],
                metadata=metadata,
                embedding=results["embeddings"][0] if results["embeddings"] else None,
                timestamp=timestamp
            )
        return None
    
    def count(self) -> int:
        return self._collection.count()


class MockVectorStore(VectorStoreBase):
    """Mock vector store for testing without external dependencies."""
    
    def __init__(self):
        self._documents: Dict[str, VectorDocument] = {}
    
    def add(self, documents: List[VectorDocument]) -> List[str]:
        ids = []
        for doc in documents:
            doc_id = doc.id or str(uuid.uuid4())
            doc.id = doc_id
            self._documents[doc_id] = doc
            ids.append(doc_id)
        return ids
    
    def search(
        self,
        query_embedding: List[float],
        limit: int = 10,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[VectorDocument]:
        results = []
        for doc in self._documents.values():
            if filter_metadata:
                match = True
                for key, value in filter_metadata.items():
                    if doc.metadata.get(key) != value:
                        match = False
                        break
                if not match:
                    continue
            results.append(doc)
            if len(results) >= limit:
                break
        return results
    
    def delete(self, ids: List[str]) -> bool:
        for id in ids:
            self._documents.pop(id, None)
        return True
    
    def get(self, id: str) -> Optional[VectorDocument]:
        return self._documents.get(id)
    
    def count(self) -> int:
        return len(self._documents)


def get_vector_store(
    provider: str = "mock",
    **kwargs
) -> VectorStoreBase:
    """Factory function to get vector store instance."""
    
    if provider == "qdrant":
        return QdrantVectorStore(**kwargs)
    elif provider == "chroma":
        return ChromaVectorStore(**kwargs)
    elif provider == "mock":
        return MockVectorStore()
    else:
        raise ValueError(f"Unknown vector store provider: {provider}")


def create_embedding(text: str, provider: str = "openai", **kwargs) -> List[float]:
    """Create embedding for text using specified provider."""
    
    if provider == "openai":
        try:
            from openai import OpenAI
            client = OpenAI(api_key=kwargs.get("api_key") or os.getenv("OPENAI_API_KEY"))
            response = client.embeddings.create(
                model=kwargs.get("model", "text-embedding-3-small"),
                input=text
            )
            return response.data[0].embedding
        except ImportError:
            raise ImportError("openai not installed. pip install openai")
    
    elif provider == "gemini":
        try:
            from google import genai
            client = genai.Client(api_key=kwargs.get("api_key") or os.getenv("GEMINI_API_KEY"))
            result = client.models.embed_content(
                model=kwargs.get("model", "text-embedding-004"),
                contents=text
            )
            return result.embeddings[0].values
        except ImportError:
            raise ImportError("google-genai not installed. pip install google-genai")
    
    elif provider == "mock":
        import hashlib
        hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
        import random
        random.seed(hash_val)
        return [random.uniform(-1, 1) for _ in range(1536)]
    
    else:
        raise ValueError(f"Unknown embedding provider: {provider}")