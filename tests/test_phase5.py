"""
Phase 5 Tests - Semantic Memory, Knowledge Graph, OCR, Consolidation
Tests for: vector search, KG entities/relations, temporal recall, summaries, OCR
Run: python -m pytest tests/test_phase5.py -v
"""

import os
import sys
import time
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.memory import Memory
from core.memory.semantic import get_semantic_memory, SemanticMemory
from core.memory.knowledge_graph import KnowledgeGraph, Entity, Relation
from core.memory.vector_store import get_vector_store, create_embedding, MockVectorStore
from core.memory.consolidation import get_consolidator, MemoryConsolidator
from core.chat_engine import ChatEngine
from providers.mock_provider import MockProvider
from core.system.screen import get_screen_analyzer


# ===== FIXTURES =====

@pytest.fixture
def temp_db(tmp_path):
    """Temporary database path."""
    return str(tmp_path / "test_phase5.db")


@pytest.fixture
def mock_provider():
    return MockProvider()


@pytest.fixture
def semantic_memory(mock_provider):
    """Semantic memory with mock embeddings."""
    return get_semantic_memory(
        embedding_provider="mock",
        llm_provider=mock_provider,
        db_path="test_phase5.db"
    )


@pytest.fixture
def chat_engine(temp_db, mock_provider):
    memory = Memory(db_path=temp_db)
    return ChatEngine(provider=mock_provider, memory=memory, enable_semantic_memory=True)


# ===== VECTOR STORE TESTS =====

def test_vector_store_mock():
    """Test MockVectorStore basic operations."""
    store = MockVectorStore()
    
    # Add documents
    from core.memory.vector_store import VectorDocument
    docs = [
        VectorDocument(id="", content="Ansh likes dark mode", metadata={"type": "preference"}),
        VectorDocument(id="", content="Spider-Man 2 is a great movie", metadata={"type": "movie"}),
    ]
    ids = store.add(docs)
    assert len(ids) == 2
    
    # Search
    query_emb = create_embedding("dark mode", provider="mock")
    results = store.search(query_emb, limit=5)
    assert len(results) >= 1
    assert "dark mode" in results[0].content.lower()
    
    # Count
    assert store.count() == 2


def test_embedding_creation():
    """Test embedding creation with mock provider."""
    emb = create_embedding("test text", provider="mock")
    assert isinstance(emb, list)
    assert len(emb) == 1536
    assert all(isinstance(x, float) for x in emb)


# ===== KNOWLEDGE GRAPH TESTS =====

def test_knowledge_graph_entities(tmp_path):
    """Test KG entity add/update/search."""
    kg = KnowledgeGraph(db_path=str(tmp_path / "test_kg.db"))
    
    # Add entity
    entity = Entity(id="", name="Ansh Kesharwani", type="person", 
                   properties={"role": "developer"}, confidence=0.9)
    eid = kg.add_entity(entity)
    assert eid
    
    # Add same entity again (should update)
    entity2 = Entity(id="", name="Ansh Kesharwani", type="person",
                    properties={"project": "Indus"}, confidence=0.8)
    eid2 = kg.add_entity(entity2)
    assert eid2 == eid  # Same ID
    
    # Search
    results = kg.search_entities("Ansh", limit=5)
    assert len(results) == 1
    assert results[0].name == "Ansh Kesharwani"
    assert results[0].mention_count == 2
    assert "project" in results[0].properties


def test_knowledge_graph_relations(tmp_path):
    """Test KG relations."""
    kg = KnowledgeGraph(db_path=str(tmp_path / "test_kg2.db"))
    
    # Add entities
    e1 = Entity(id="", name="Ansh", type="person", properties={})
    e2 = Entity(id="", name="Indus", type="software", properties={})
    id1 = kg.add_entity(e1)
    id2 = kg.add_entity(e2)
    
    # Add relation
    rel = Relation(id="", source_id=id1, target_id=id2, 
                  relation_type="created", properties={})
    rel_id = kg.add_relation(rel)
    assert rel_id
    
    # Get relations
    relations = kg.get_relations(id1)
    assert len(relations) == 1
    assert relations[0][0].relation_type == "created"
    assert relations[0][1].name == "Indus"


def test_knowledge_graph_stats(tmp_path):
    """Test KG statistics."""
    kg = KnowledgeGraph(db_path=str(tmp_path / "test_kg3.db"))
    
    kg.add_entity(Entity(id="", name="Test1", type="person", properties={}))
    kg.add_entity(Entity(id="", name="Test2", type="concept", properties={}))
    
    stats = kg.get_stats()
    assert stats["total_entities"] == 2
    assert stats["entity_types"]["person"] == 1
    assert stats["entity_types"]["concept"] == 1


# ===== SEMANTIC MEMORY TESTS =====

def test_semantic_memory_add_conversation(semantic_memory):
    """Test adding conversation to semantic memory."""
    ids = semantic_memory.add_conversation(
        user_message="What is my favorite movie?",
        assistant_response="Your favorite movie is The Amazing Spider-Man 2",
        metadata={"topic": "movies"}
    )
    assert len(ids) == 1


def test_semantic_memory_search(semantic_memory, mock_provider):
    """Test semantic search."""
    # Add some conversations
    semantic_memory.add_conversation(
        "I love Python programming",
        "Python is great for AI development"
    )
    semantic_memory.add_conversation(
        "The Amazing Spider-Man 2 is my favorite movie",
        "Great choice! Andrew Garfield's Spider-Man is underrated"
    )
    
    # Search
    results = semantic_memory.search("Python", limit=5)
    assert len(results) >= 1
    
    results = semantic_memory.search("Spider-Man", limit=5)
    assert len(results) >= 1


def test_semantic_memory_temporal_recall(semantic_memory):
    """Test temporal recall (date, week, month)."""
    from datetime import datetime, timedelta
    
    today = datetime.now().strftime("%Y-%m-%d")
    results = semantic_memory.recall_date(today, limit=10)
    assert isinstance(results, list)
    
    week = datetime.now().strftime("%Y-W%U")
    results = semantic_memory.recall_week(week, limit=10)
    assert isinstance(results, list)
    
    month = datetime.now().strftime("%Y-%m")
    results = semantic_memory.recall_month(month, limit=10)
    assert isinstance(results, list)


def test_semantic_memory_summary(semantic_memory):
    """Test summary generation."""
    summary = semantic_memory.get_summary(period="week")
    assert isinstance(summary, str)
    assert len(summary) > 0


def test_semantic_memory_learn_fact(semantic_memory):
    """Test explicit fact learning."""
    result = semantic_memory.learn_fact("Ansh prefers dark mode theme", "preference")
    assert "Learned fact" in result
    
    # Search for it
    results = semantic_memory.search("dark mode", limit=5)
    assert len(results) >= 1


def test_semantic_memory_stats(semantic_memory):
    """Test memory statistics."""
    stats = semantic_memory.get_stats()
    assert "vector_store_count" in stats
    assert "knowledge_graph" in stats
    assert "total_entities" in stats["knowledge_graph"]


# ===== CONSOLIDATION TESTS =====

def test_consolidation_basic(temp_db, mock_provider):
    """Test memory consolidation."""
    memory = Memory(db_path=temp_db)
    semantic = get_semantic_memory(embedding_provider="mock", llm_provider=mock_provider, db_path=temp_db)
    
    # Add some messages
    memory.save_message("user", "Hello")
    memory.save_message("assistant", "Hi there")
    memory.save_message("user", "My name is Ansh")
    memory.save_message("assistant", "Nice to meet you Ansh")
    
    # Run consolidation
    consolidator = MemoryConsolidator(memory, semantic, mock_provider, batch_size=10, interval_minutes=60)
    job = consolidator.force_consolidation(since_id=0)
    
    # force_consolidation returns None (submits to executor), get job from stats
    import time
    start = time.time()
    while time.time() - start < 30:
        stats = consolidator.get_stats()
        if stats["total_jobs"] > 0 and stats["completed"] > 0:
            break
        time.sleep(0.5)
    
    stats = consolidator.get_stats()
    assert stats["total_jobs"] >= 1
    assert stats["completed"] >= 1
    assert stats["total_items_processed"] >= 1


def test_consolidation_stats(temp_db, mock_provider):
    """Test consolidation statistics."""
    memory = Memory(db_path=temp_db)
    semantic = get_semantic_memory(embedding_provider="mock", llm_provider=mock_provider, db_path=temp_db)
    
    consolidator = get_consolidator(memory, semantic, mock_provider)
    stats = consolidator.get_stats()
    
    assert "total_jobs" in stats
    assert "total_items_processed" in stats
    assert "last_consolidated_id" in stats


# ===== CHAT ENGINE INTEGRATION TESTS =====

def test_chat_engine_semantic_integration(chat_engine):
    """Test ChatEngine with semantic memory enabled."""
    # Have a conversation
    chat_engine.respond("My name is Ansh")
    chat_engine.respond("I am building Indus AI")
    
    # Check semantic memory was updated
    assert chat_engine.semantic_memory is not None
    stats = chat_engine.semantic_memory.get_stats()
    assert stats["vector_store_count"] >= 1


def test_chat_engine_memory_skills(chat_engine):
    """Test memory skills through ChatEngine."""
    # These would be triggered via intent parsing
    # For now, test direct skill access
    from core.memory.semantic import get_semantic_memory
    
    semantic = get_semantic_memory(embedding_provider="mock", llm_provider=MockProvider(), db_path="test_phase5.db")
    
    # Learn fact
    result = semantic.learn_fact("Test fact for skill", "test")
    assert "Learned fact" in result
    
    # Search
    results = semantic.search("Test fact", limit=5)
    assert len(results) >= 1


# ===== OCR / SCREEN ANALYSIS TESTS =====

def test_screen_capture():
    """Test screen capture."""
    analyzer = get_screen_analyzer("tesseract")
    image = analyzer.capture_full_screen()
    assert image is not None
    assert image.size[0] > 0
    assert image.size[1] > 0


def test_ocr_tesseract():
    """Test OCR with Tesseract (if available)."""
    analyzer = get_screen_analyzer("tesseract")
    image = analyzer.capture_full_screen()
    
    text = analyzer.ocr(image)
    # OCR may return empty if Tesseract not installed, but shouldn't error
    assert isinstance(text, str)


def test_read_screen_skill():
    """Test ReadScreenSkill."""
    from core.skills.system import ReadScreenSkill
    skill = ReadScreenSkill()
    
    result = skill.execute(mode="ocr", region="full")
    assert isinstance(result, str)
    # Should either return text or error message
    assert len(result) > 0


# ===== ENTITY EXTRACTION TESTS =====

def test_entity_extraction_with_llm(mock_provider):
    """Test LLM-based entity extraction."""
    from core.memory.knowledge_graph import extract_with_llm
    
    text = "Ansh Kesharwani created Indus AI assistant. He works on Python projects."
    entities, relations = extract_with_llm(text, mock_provider)
    
    # Mock provider returns mock response, so entities may be empty
    # But shouldn't error
    assert isinstance(entities, list)
    assert isinstance(relations, list)


# ===== MAIN =====

if __name__ == "__main__":
    pytest.main([__file__, "-v"])