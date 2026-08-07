"""
Memory Package - Long-term semantic memory system
"""

from .memory import Memory
from .vector_store import (
    VectorStoreBase,
    VectorDocument,
    QdrantVectorStore,
    ChromaVectorStore,
    MockVectorStore,
    get_vector_store,
    create_embedding
)
from .knowledge_graph import (
    KnowledgeGraph,
    Entity,
    Relation,
    extract_entities_and_relations,
    extract_with_llm
)
from .semantic import (
    SemanticMemory,
    MemorySearchResult,
    get_semantic_memory
)
from .consolidation import (
    MemoryConsolidator,
    ConsolidationJob,
    get_consolidator
)

__all__ = [
    "Memory",
    "VectorStoreBase",
    "VectorDocument",
    "QdrantVectorStore",
    "ChromaVectorStore",
    "MockVectorStore",
    "get_vector_store",
    "create_embedding",
    "KnowledgeGraph",
    "Entity",
    "Relation",
    "extract_entities_and_relations",
    "extract_with_llm",
    "SemanticMemory",
    "MemorySearchResult",
    "get_semantic_memory",
    "MemoryConsolidator",
    "ConsolidationJob",
    "get_consolidator",
]