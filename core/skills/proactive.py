"""
Proactive Skills - Context monitoring, routines, suggestions, plugins
"""

from typing import List, Dict, Any
from core.skills.base import BaseSkill, SkillParameter


class ProactiveStartSkill(BaseSkill):
    """Start proactive suggestion engine."""
    
    @property
    def name(self) -> str:
        return "proactive.start"
    
    @property
    def description(self) -> str:
        return "Start background proactive intelligence (context monitoring, routine learning, suggestions)"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="interval",
                type="number",
                description="Context check interval in seconds",
                required=False,
                default=30,
            ),
        ]
    
    @property
    def category(self) -> str:
        return "proactive"
    
    @property
    def examples(self) -> List[str]:
        return [
            "Start proactive assistant",
            "Enable proactive suggestions",
        ]
    
    def execute(self, interval: int = 30) -> str:
        try:
            from core.proactive import get_suggestion_engine
            engine = get_suggestion_engine()
            engine.start()
            return f"Proactive engine started (context check every {interval}s)"
        except Exception as e:
            return f"Failed to start proactive engine: {e}"


class ProactiveStopSkill(BaseSkill):
    """Stop proactive suggestion engine."""
    
    @property
    def name(self) -> str:
        return "proactive.stop"
    
    @property
    def description(self) -> str:
        return "Stop background proactive intelligence"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return []
    
    @property
    def category(self) -> str:
        return "proactive"
    
    @property
    def examples(self) -> List[str]:
        return [
            "Stop proactive assistant",
            "Disable proactive suggestions",
        ]
    
    def execute(self) -> str:
        try:
            from core.proactive import get_suggestion_engine
            engine = get_suggestion_engine()
            engine.stop()
            return "Proactive engine stopped"
        except Exception as e:
            return f"Failed to stop proactive engine: {e}"


class ProactiveSuggestionsSkill(BaseSkill):
    """Get current proactive suggestions."""
    
    @property
    def name(self) -> str:
        return "proactive.suggestions"
    
    @property
    def description(self) -> str:
        return "Get current proactive suggestions"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="limit",
                type="number",
                description="Max suggestions to return",
                required=False,
                default=5,
            ),
            SkillParameter(
                name="action",
                type="string",
                description="Action: 'list', 'dismiss', 'execute'",
                required=False,
                default="list",
                enum=["list", "dismiss", "execute"],
            ),
            SkillParameter(
                name="suggestion_id",
                type="string",
                description="Suggestion ID for dismiss/execute",
                required=False,
                default="",
            ),
        ]
    
    @property
    def category(self) -> str:
        return "proactive"
    
    @property
    def examples(self) -> List[str]:
        return [
            "Show proactive suggestions",
            "What do you suggest?",
            "Dismiss suggestion",
        ]
    
    def execute(self, action: str = "list", limit: int = 5, suggestion_id: str = "") -> str:
        try:
            from core.proactive import get_suggestion_engine
            engine = get_suggestion_engine()
            
            if action == "list":
                suggestions = engine.get_pending_suggestions(limit)
                if not suggestions:
                    return "No pending suggestions"
                
                lines = ["Proactive Suggestions:"]
                for i, s in enumerate(suggestions, 1):
                    lines.append(f"  {i}. [{s.type.value}] {s.title}")
                    lines.append(f"     {s.description}")
                    lines.append(f"     Confidence: {s.confidence:.0%} | ID: {s.id}")
                return "\n".join(lines)
            
            elif action == "dismiss":
                if not suggestion_id:
                    return "suggestion_id required for dismiss"
                engine.dismiss_suggestion(suggestion_id)
                return f"Dismissed suggestion {suggestion_id}"
            
            elif action == "execute":
                if not suggestion_id:
                    return "suggestion_id required for execute"
                if engine.execute_suggestion(suggestion_id):
                    return f"Executed suggestion {suggestion_id}"
                return f"Suggestion {suggestion_id} not found"
            
            return f"Unknown action: {action}"
        except Exception as e:
            return f"Failed to get suggestions: {e}"


class RoutineAnalyzeSkill(BaseSkill):
    """Analyze and learn user routines."""
    
    @property
    def name(self) -> str:
        return "proactive.analyze_routines"
    
    @property
    def description(self) -> str:
        return "Analyze user behavior patterns and learn routines"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="days",
                type="number",
                description="Days of history to analyze",
                required=False,
                default=7,
            ),
        ]
    
    @property
    def category(self) -> str:
        return "proactive"
    
    @property
    def examples(self) -> List[str]:
        return [
            "Analyze my routines",
            "Learn my patterns",
        ]
    
    def execute(self, days: int = 7) -> str:
        try:
            from core.proactive import get_routine_learner
            learner = get_routine_learner()
            patterns = learner.analyze_patterns(lookback_days=days)
            
            if not patterns:
                return f"No new routines found in last {days} days"
            
            lines = [f"Found {len(patterns)} new routine patterns:"]
            for p in patterns:
                actions_str = " -> ".join(f"{a['type']}:{a['target']}" for a in p.actions)
                lines.append(f"  {p.name}: {actions_str} (confidence: {p.confidence:.0%}, seen {p.occurrences}x)")
            return "\n".join(lines)
        except Exception as e:
            return f"Failed to analyze routines: {e}"


class RoutineStatsSkill(BaseSkill):
    """Get routine learner statistics."""
    
    @property
    def name(self) -> str:
        return "proactive.routine_stats"
    
    @property
    def description(self) -> str:
        return "Get statistics about learned routines"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return []
    
    @property
    def category(self) -> str:
        return "proactive"
    
    @property
    def examples(self) -> List[str]:
        return [
            "Routine statistics",
            "Show learned patterns",
        ]
    
    def execute(self) -> str:
        try:
            from core.proactive import get_routine_learner
            learner = get_routine_learner()
            stats = learner.get_stats()
            
            lines = ["Routine Learner Stats:"]
            for k, v in stats.items():
                lines.append(f"  {k}: {v}")
            
            # Show patterns
            if hasattr(learner, '_patterns'):
                lines.append(f"\nPatterns ({len(learner._patterns)}):")
                for p in learner._patterns:
                    actions_str = " -> ".join(f"{a['type']}:{a['target']}" for a in p.actions)
                    lines.append(f"  {p.name}: {actions_str} (conf: {p.confidence:.0%}, {p.occurrences}x)")
            
            return "\n".join(lines)
        except Exception as e:
            return f"Failed to get routine stats: {e}"


class ContextStatusSkill(BaseSkill):
    """Get current context monitoring status."""
    
    @property
    def name(self) -> str:
        return "proactive.context_status"
    
    @property
    def description(self) -> str:
        return "Get current system context (active app, time, idle, etc.)"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return []
    
    @property
    def category(self) -> str:
        return "proactive"
    
    @property
    def examples(self) -> List[str]:
        return [
            "Current context",
            "What am I doing?",
        ]
    
    def execute(self) -> str:
        try:
            from core.proactive import get_context_monitor
            monitor = get_context_monitor()
            snapshot = monitor.get_current_context()
            
            if not snapshot:
                return "No context captured yet"
            
            lines = ["Current Context:"]
            lines.append(f"  Active App: {snapshot.active_app or 'Unknown'}")
            lines.append(f"  Window: {snapshot.window_title or 'Unknown'}")
            lines.append(f"  Time: {snapshot.time_of_day} ({snapshot.day_of_week})")
            lines.append(f"  Idle: {snapshot.user_idle_seconds:.0f}s")
            
            history = monitor.get_history(5)
            if history:
                lines.append(f"\nRecent History ({len(history)} snapshots):")
                for h in history[-5:]:
                    dt = __import__('datetime').datetime.fromtimestamp(h.timestamp)
                    lines.append(f"  {dt.strftime('%H:%M:%S')} - {h.active_app} - {h.window_title[:50]}")
            
            return "\n".join(lines)
        except Exception as e:
            return f"Failed to get context: {e}"


class PluginLoadSkill(BaseSkill):
    """Load community plugins."""
    
    @property
    def name(self) -> str:
        return "plugin.load"
    
    @property
    def description(self) -> str:
        return "Load community skill plugins"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="action",
                type="string",
                description="Action: 'discover', 'load', 'list', 'load_all'",
                required=True,
                enum=["discover", "load", "list", "load_all"],
            ),
            SkillParameter(
                name="plugin_path",
                type="string",
                description="Path to plugin (for 'load' action)",
                required=False,
                default="",
            ),
        ]
    
    @property
    def category(self) -> str:
        return "plugin"
    
    @property
    def examples(self) -> List[str]:
        return [
            "Discover plugins",
            "Load all plugins",
            "List loaded plugins",
        ]
    
    def execute(self, action: str, plugin_path: str = "") -> str:
        try:
            from core.plugins import get_plugin_loader
            loader = get_plugin_loader()
            
            if action == "discover":
                plugins = loader.discover_plugins()
                if not plugins:
                    return "No plugins found"
                return f"Discovered {len(plugins)} plugins:\n" + "\n".join(f"  {p}" for p in plugins)
            
            elif action == "load_all":
                results = loader.load_all_plugins()
                loaded = sum(1 for r in results if not r["errors"])
                return f"Loaded {loaded}/{len(results)} plugins"
            
            elif action == "load":
                if not plugin_path:
                    return "plugin_path required for load"
                result = loader.load_plugin(plugin_path)
                if result["errors"]:
                    return f"Errors: {result['errors']}"
                skills = [s.name for s in result["skills"]]
                return f"Loaded plugin: {len(skills)} skills - {', '.join(skills)}"
            
            elif action == "list":
                skills = loader.get_all_skills()
                if not skills:
                    return "No skills loaded from plugins"
                lines = ["Plugin Skills:"]
                for s in skills:
                    lines.append(f"  {s.name}: {s.description}")
                return "\n".join(lines)
            
            return f"Unknown action: {action}"
        except Exception as e:
            return f"Plugin error: {e}"


def register_proactive_skills(registry) -> None:
    """Register all proactive skills."""
    skills = [
        ProactiveStartSkill(),
        ProactiveStopSkill(),
        ProactiveSuggestionsSkill(),
        RoutineAnalyzeSkill(),
        RoutineStatsSkill(),
        ContextStatusSkill(),
        PluginLoadSkill(),
    ]
    
    for skill in skills:
        registry.register(skill.to_definition())