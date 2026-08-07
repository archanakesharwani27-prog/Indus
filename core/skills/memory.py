"""
Memory Skills - Semantic memory search, recall, summaries, fact learning
"""

from typing import List
from core.skills.base import BaseSkill, SkillParameter


class MemorySearchSkill(BaseSkill):
    """Semantic search across all conversation history."""
    
    @property
    def name(self) -> str:
        return "memory.search"
    
    @property
    def description(self) -> str:
        return "Search conversation history semantically (what did I say about X?)"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="query",
                type="string",
                description="Search query (natural language)",
                required=True,
            ),
            SkillParameter(
                name="limit",
                type="number",
                description="Maximum results to return",
                required=False,
                default=10,
            ),
        ]
    
    @property
    def category(self) -> str:
        return "memory"
    
    @property
    def examples(self) -> List[str]:
        return [
            "What did I say about python last month?",
            "Search for meeting notes about project alpha",
            "Find conversations about restaurant recommendations",
        ]
    
    def execute(self, query: str, limit: int = 10) -> str:
        try:
            from core.memory.semantic import get_semantic_memory
            semantic = get_semantic_memory()
            results = semantic.search(query, limit=limit)
            
            if not results:
                return f"No memories found for: {query}"
            
            lines = [f"Found {len(results)} memories for '{query}':"]
            for i, result in enumerate(results, 1):
                preview = result.content[:200] + "..." if len(result.content) > 200 else result.content
                lines.append(f"\n{i}. [{result.source}] {result.timestamp[:19]}")
                lines.append(f"   {preview}")
            
            return "\n".join(lines)
        except Exception as e:
            return f"Memory search failed: {e}"


class MemoryRecallDateSkill(BaseSkill):
    """Recall memories from a specific date."""
    
    @property
    def name(self) -> str:
        return "memory.recall_date"
    
    @property
    def description(self) -> str:
        return "Recall all memories from a specific date (YYYY-MM-DD)"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="date",
                type="string",
                description="Date in YYYY-MM-DD format",
                required=True,
            ),
            SkillParameter(
                name="limit",
                type="number",
                description="Maximum memories to return",
                required=False,
                default=20,
            ),
        ]
    
    @property
    def category(self) -> str:
        return "memory"
    
    @property
    def examples(self) -> List[str]:
        return [
            "What happened on 2025-08-15?",
            "Show me memories from yesterday",
            "Recall 2024-12-25",
        ]
    
    def execute(self, date: str, limit: int = 20) -> str:
        try:
            from core.memory.semantic import get_semantic_memory
            semantic = get_semantic_memory()
            
            # Handle relative dates
            from datetime import datetime, timedelta
            if date.lower() == "yesterday":
                date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            elif date.lower() == "today":
                date = datetime.now().strftime("%Y-%m-%d")
            
            results = semantic.recall_date(date, limit=limit)
            
            if not results:
                return f"No memories found for {date}"
            
            lines = [f"Memories from {date} ({len(results)} found):"]
            for i, result in enumerate(results, 1):
                preview = result.content[:200] + "..." if len(result.content) > 200 else result.content
                lines.append(f"\n{i}. {result.timestamp[:19]}")
                lines.append(f"   {preview}")
            
            return "\n".join(lines)
        except Exception as e:
            return f"Date recall failed: {e}"


class MemoryRecallWeekSkill(BaseSkill):
    """Recall memories from a specific week."""
    
    @property
    def name(self) -> str:
        return "memory.recall_week"
    
    @property
    def description(self) -> str:
        return "Recall memories from a specific week (YYYY-WW)"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="week",
                type="string",
                description="Week in YYYY-WW format (e.g., 2025-32)",
                required=True,
            ),
            SkillParameter(
                name="limit",
                type="number",
                description="Maximum memories to return",
                required=False,
                default=30,
            ),
        ]
    
    @property
    def category(self) -> str:
        return "memory"
    
    @property
    def examples(self) -> List[str]:
        return [
            "What happened last week?",
            "Show week 2025-32",
        ]
    
    def execute(self, week: str, limit: int = 30) -> str:
        try:
            from core.memory.semantic import get_semantic_memory
            from datetime import datetime
            
            semantic = get_semantic_memory()
            
            if week.lower() == "last week":
                last_week = datetime.now() - timedelta(weeks=1)
                week = last_week.strftime("%Y-W%U")
            elif week.lower() == "this week":
                week = datetime.now().strftime("%Y-W%U")
            
            results = semantic.recall_week(week, limit=limit)
            
            if not results:
                return f"No memories found for week {week}"
            
            lines = [f"Memories from week {week} ({len(results)} found):"]
            for i, result in enumerate(results, 1):
                preview = result.content[:200] + "..." if len(result.content) > 200 else result.content
                lines.append(f"\n{i}. {result.timestamp[:19]}")
                lines.append(f"   {preview}")
            
            return "\n".join(lines)
        except Exception as e:
            return f"Week recall failed: {e}"


from datetime import timedelta


class MemoryRecallMonthSkill(BaseSkill):
    """Recall memories from a specific month."""
    
    @property
    def name(self) -> str:
        return "memory.recall_month"
    
    @property
    def description(self) -> str:
        return "Recall memories from a specific month (YYYY-MM)"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="month",
                type="string",
                description="Month in YYYY-MM format (e.g., 2025-08)",
                required=True,
            ),
            SkillParameter(
                name="limit",
                type="number",
                description="Maximum memories to return",
                required=False,
                default=50,
            ),
        ]
    
    @property
    def category(self) -> str:
        return "memory"
    
    @property
    def examples(self) -> List[str]:
        return [
            "What happened last month?",
            "Show August 2025 memories",
        ]
    
    def execute(self, month: str, limit: int = 50) -> str:
        try:
            from core.memory.semantic import get_semantic_memory
            from datetime import datetime
            
            semantic = get_semantic_memory()
            
            if month.lower() == "last month":
                first_this_month = datetime.now().replace(day=1)
                last_month = first_this_month - timedelta(days=1)
                month = last_month.strftime("%Y-%m")
            elif month.lower() == "this month":
                month = datetime.now().strftime("%Y-%m")
            
            results = semantic.recall_month(month, limit=limit)
            
            if not results:
                return f"No memories found for {month}"
            
            lines = [f"Memories from {month} ({len(results)} found):"]
            for i, result in enumerate(results, 1):
                preview = result.content[:200] + "..." if len(result.content) > 200 else result.content
                lines.append(f"\n{i}. {result.timestamp[:19]}")
                lines.append(f"   {preview}")
            
            return "\n".join(lines)
        except Exception as e:
            return f"Month recall failed: {e}"


class MemorySummarySkill(BaseSkill):
    """Generate summary of memories for a time period."""
    
    @property
    def name(self) -> str:
        return "memory.get_summary"
    
    @property
    def description(self) -> str:
        return "Generate AI summary of memories for day/week/month/year"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="period",
                type="string",
                description="Period: day, week, month, year",
                required=True,
                enum=["day", "week", "month", "year"],
            ),
            SkillParameter(
                name="date",
                type="string",
                description="Reference date (YYYY-MM-DD), defaults to today",
                required=False,
                default="",
            ),
        ]
    
    @property
    def category(self) -> str:
        return "memory"
    
    @property
    def examples(self) -> List[str]:
        return [
            "Summarize last week",
            "Weekly summary",
            "Month summary for 2025-08",
            "Year in review",
        ]
    
    def execute(self, period: str, date: str = "") -> str:
        try:
            from core.memory.semantic import get_semantic_memory
            semantic = get_semantic_memory()
            
            ref_date = date if date else None
            summary = semantic.get_summary(period=period, reference_date=ref_date)
            
            return f"{period.capitalize()} summary:\n{summary}"
        except Exception as e:
            return f"Summary generation failed: {e}"


class MemoryLearnFactSkill(BaseSkill):
    """Explicitly store a fact in long-term memory."""
    
    @property
    def name(self) -> str:
        return "memory.learn_fact"
    
    @property
    def description(self) -> str:
        return "Explicitly remember a fact for future recall"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="fact",
                type="string",
                description="The fact to remember",
                required=True,
            ),
            SkillParameter(
                name="category",
                type="string",
                description="Category: general, preference, contact, project, etc.",
                required=False,
                default="general",
            ),
        ]
    
    @property
    def category(self) -> str:
        return "memory"
    
    @property
    def examples(self) -> List[str]:
        return [
            "Remember that I prefer dark mode",
            "Remember Ansh's birthday is March 15",
            "Remember project deadline is Friday",
        ]
    
    def execute(self, fact: str, category: str = "general") -> str:
        try:
            from core.memory.semantic import get_semantic_memory
            semantic = get_semantic_memory()
            return semantic.learn_fact(fact, category)
        except Exception as e:
            return f"Learning fact failed: {e}"


class MemoryStatsSkill(BaseSkill):
    """Get memory system statistics."""
    
    @property
    def name(self) -> str:
        return "memory.stats"
    
    @property
    def description(self) -> str:
        return "Get statistics about semantic memory system"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return []
    
    @property
    def category(self) -> str:
        return "memory"
    
    @property
    def examples(self) -> List[str]:
        return [
            "Memory stats",
            "How much do you remember?",
        ]
    
    def execute(self) -> str:
        try:
            from core.memory.semantic import get_semantic_memory
            from core.memory.consolidation import get_consolidator
            from core.memory import Memory
            
            semantic = get_semantic_memory()
            stats = semantic.get_stats()
            
            lines = ["Memory System Statistics:"]
            lines.append(f"  Vector Store: {stats['vector_store_count']} documents")
            
            kg = stats['knowledge_graph']
            lines.append(f"  Knowledge Graph:")
            lines.append(f"    Entities: {kg['total_entities']}")
            lines.append(f"    Relations: {kg['total_relations']}")
            lines.append(f"    Entity Types: {kg['entity_types']}")
            lines.append(f"    Relation Types: {kg['relation_types']}")
            
            # Consolidation stats
            try:
                memory = Memory(db_path="indus.db")
                consolidator = get_consolidator(memory, semantic)
                cstats = consolidator.get_stats()
                lines.append(f"  Consolidation:")
                lines.append(f"    Jobs: {cstats['total_jobs']} (completed: {cstats['completed']})")
                lines.append(f"    Items Processed: {cstats['total_items_processed']}")
                lines.append(f"    Last Consolidated ID: {cstats['last_consolidated_id']}")
            except Exception:
                pass
            
            return "\n".join(lines)
        except Exception as e:
            return f"Stats failed: {e}"


def register_memory_skills(registry) -> None:
    """Register all memory skills."""
    skills = [
        MemorySearchSkill(),
        MemoryRecallDateSkill(),
        MemoryRecallWeekSkill(),
        MemoryRecallMonthSkill(),
        MemorySummarySkill(),
        MemoryLearnFactSkill(),
        MemoryStatsSkill(),
    ]
    
    for skill in skills:
        registry.register(skill.to_definition())