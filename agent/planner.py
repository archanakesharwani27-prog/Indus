# agent/planner.py
"""
INDUS Intelligent Task Planner
Generates structured, validated execution plans for complex user goals,
injecting permanent user memories and formatting into TaskStep representations.
"""

import json
import logging
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from agent.task_model import TaskStep, agent_context

logger = logging.getLogger("IndusPlanner")

def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

BASE_DIR = _get_base_dir()
CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"

VALID_TOOLS = {
    "open_app", "computer_control", "computer_settings", "vision_click", "vision_type",
    "vision_scroll", "vision_engine", "vision_find_element", "screen_understand", "deep_research", "web_search",
    "youtube_video", "live_writer", "teleport_workspace", "mobile_bridge",
    "file_controller", "code_helper", "reminder", "weather_report", "flight_finder",
    "smart_home", "security_vault", "bluetooth_control", "browser_control",
    "cmd_control", "desktop_control", "send_message", "terminal_command"
}

PLANNER_SYSTEM_PROMPT = """You are the Lead Planning Engine of INDUS, an autonomous personal AI assistant.
Your task: Decompose complex user goals into minimal, high-precision sequential steps using ONLY the registered tools.

RULES:
1. Use minimum steps needed. Maximum 6 steps.
2. Every step must be self-contained with exact parameters.
3. For interacting with UI visually:
   - To click buttons, links, or elements: use 'vision_click' (target: '<element description>').
   - To type in search boxes, URL bars, or textboxes: use 'vision_type' (target: '<field description>', text: '<text>', press_enter: true/false).
   - To scroll feeds or pages: use 'vision_scroll' (direction: 'down'/'up', amount: 300).
4. For launching software, use 'open_app' (app_name: '<app>').
5. For system volume/brightness, use 'computer_settings' (action: 'volume_set', 'brightness_set').
6. For playing songs/videos, use 'youtube_video' (action: 'play').
7. For research and real-time facts, use 'deep_research' or 'web_search'.

OUTPUT SCHEMA:
Return ONLY valid JSON matching this schema:
{
  "goal": "<exact goal>",
  "steps": [
    {
      "step_id": 1,
      "tool": "<tool_name>",
      "description": "<what this step achieves>",
      "parameters": {"<key>": "<value>"},
      "expected_result": "<concrete observable state after execution>",
      "critical": true
    }
  ]
}
"""

CANDIDATE_MODELS = [
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-flash-latest",
]


def _get_api_key() -> str:
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f).get("gemini_api_key", "").strip()
    except Exception:
        return ""


def _retrieve_memory_context(goal: str) -> str:
    """Retrieve relevant user habits, preferences, and profiles to personalize the plan."""
    try:
        from memory.memory_manager import load_memory, format_memory_for_prompt
        memory_data = load_memory()
        formatted = format_memory_for_prompt(memory_data)
        if formatted:
            return f"\nRelevant User Profile & Preferences:\n{formatted}"
    except Exception:
        pass
    return ""


def validate_plan_schema(plan: dict) -> List[TaskStep]:
    """Validate model output, strip hallucinations, and convert to TaskStep list."""
    if not isinstance(plan, dict) or "steps" not in plan or not isinstance(plan["steps"], list):
        raise ValueError("Plan missing valid 'steps' list.")

    valid_steps: List[TaskStep] = []
    for idx, raw in enumerate(plan["steps"], start=1):
        tool = raw.get("tool", "").strip()
        if tool not in VALID_TOOLS:
            # Fallback tool mapping
            if "search" in tool or "find" in tool:
                tool = "web_search"
            elif "click" in tool or "button" in tool:
                tool = "vision_click"
            elif "write" in tool or "code" in tool or "note" in tool:
                tool = "live_writer"
            elif "app" in tool or "open" in tool:
                tool = "open_app"
            else:
                tool = "computer_control"

        desc = raw.get("description") or f"Execute {tool}"
        params = raw.get("parameters") if isinstance(raw.get("parameters"), dict) else {}
        expected = raw.get("expected_result") or f"{desc} successfully executed"
        critical = bool(raw.get("critical", True))

        step = TaskStep(
            step_id=raw.get("step_id", idx),
            tool=tool,
            description=desc,
            parameters=params,
            expected_result=expected,
            critical=critical,
        )
        valid_steps.append(step)

    if not valid_steps:
        raise ValueError("No valid steps generated in plan.")

    return valid_steps


def _match_deterministic_pattern(goal: str) -> Optional[List[TaskStep]]:
    """Sub-millisecond direct pattern match for common system operations."""
    g_lower = goal.lower().strip()

    # 1. Temp files / cache / junk cleanup & display
    if any(k in g_lower for k in ["temp", "cache", "junk"]):
        if any(w in g_lower for w in ["delete", "clean", "remove", "clear", "hatao", "empty", "purge", "forcefully"]):
            return [TaskStep(step_id=1, tool="file_controller", description="Clean temporary files", parameters={"action": "clean_temp"})]
        elif any(w in g_lower for w in ["show", "open", "list", "dikhao", "kholo", "view"]):
            return [TaskStep(step_id=1, tool="open_app", description="Open temp folder", parameters={"app_name": "%temp%"})]

    # 2. Volume / Brightness
    if "volume" in g_lower or "brightness" in g_lower or "awaz" in g_lower:
        return [TaskStep(step_id=1, tool="computer_settings", description=goal, parameters={"action": "set", "description": goal})]

    # 3. YouTube playback
    if any(w in g_lower for w in ["play ", "chalao", "baja", "song", "gaana"]) and not any(w in g_lower for w in ["game", "cricket"]):
        song = re.sub(r"^(play|chalao|baja|song|gaana)\s*", "", g_lower).strip()
        return [TaskStep(step_id=1, tool="youtube_video", description=f"Play {song or goal}", parameters={"action": "play", "query": song or goal})]

    # 4. Live Code / Notes Writer (HTML, Python, Sudoku, Game, Code, Notes)
    if any(k in g_lower for k in ["code likho", "likho", "design kro", "design karo", "html page", "webpage", "sudoku", "game ka code", "notes banao", "document banao"]):
        return [TaskStep(step_id=1, tool="live_writer", description=goal, parameters={"topic": goal, "subject": goal, "file_type": "auto"})]

    # 5. App / Folder opening
    if g_lower.startswith("open ") or g_lower.startswith("kholo ") or g_lower.endswith(" kholo"):
        target = re.sub(r"^(open|kholo)\s*|\s*kholo$", "", g_lower).strip()
        if target:
            return [TaskStep(step_id=1, tool="open_app", description=f"Open {target}", parameters={"app_name": target})]

    return None


def create_agent_plan(goal: str, context: str = "") -> List[TaskStep]:
    """
    Generate a validated step-by-step plan for a user goal.
    Integrates memory context and anaphora resolution.
    """
    # 1. Resolve conversational anaphora ("open it", "play that")
    resolved_goal = agent_context.resolve_anaphora(goal)

    # 2. Try instant sub-millisecond deterministic fast-path
    fast_plan = _match_deterministic_pattern(resolved_goal)
    if fast_plan:
        return fast_plan

    mem_ctx = _retrieve_memory_context(resolved_goal)

    full_prompt = f"Goal: {resolved_goal}\n"
    if context:
        full_prompt += f"Context: {context}\n"
    if mem_ctx:
        full_prompt += f"{mem_ctx}\n"

    api_key = _get_api_key()
    raw_json_text = ""

    # Try Google GenAI Client with strict 4s timeout
    if api_key:
        import concurrent.futures
        try:
            from google import genai
            client = genai.Client(api_key=api_key, http_options={"api_version": "v1beta"})
            for model_name in CANDIDATE_MODELS:
                try:
                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                        future = executor.submit(
                            client.models.generate_content,
                            model=model_name,
                            contents=full_prompt,
                            config={
                                "system_instruction": PLANNER_SYSTEM_PROMPT,
                                "temperature": 0.1,
                                "response_mime_type": "application/json",
                            },
                        )
                        resp = future.result(timeout=4.0)
                    raw_json_text = resp.text.strip()
                    if raw_json_text:
                        break
                except Exception as m_err:
                    logger.debug(f"[Planner] {model_name} planning error: {m_err}")
        except Exception as e:
            logger.warning(f"[Planner] GenAI planning error: {e}")

    # Fallback to OpenRouter / Groq fast path
    if not raw_json_text:
        try:
            from or_client import client as or_c
            raw_json_text = or_c.chat(
                full_prompt,
                system=PLANNER_SYSTEM_PROMPT + "\nReturn ONLY valid JSON.",
                max_tokens=800,
                temperature=0.1,
            )
        except Exception as e:
            logger.warning(f"[Planner] OpenRouter fallback failed: {e}")

    # Parse and validate plan
    try:
        clean = raw_json_text.strip()
        if "```" in clean:
            clean = re.sub(r"^```(?:json)?\s*", "", clean)
            clean = re.sub(r"\s*```$", "", clean)
        parsed = json.loads(clean)
        return validate_plan_schema(parsed)
    except Exception as e:
        logger.warning(f"[Planner] Parsing plan failed ({e}) -> Creating single-step fallback plan.")
        return _create_fallback_plan(resolved_goal)


def _create_fallback_plan(goal: str) -> List[TaskStep]:
    """Deterministic single-step fallback plan if AI planner JSON parsing fails."""
    g_lower = goal.lower()
    if "temp" in g_lower or "cache" in g_lower or "junk" in g_lower:
        if any(w in g_lower for w in ["delete", "clean", "remove", "clear", "hatao", "forcefully"]):
            return [TaskStep(step_id=1, tool="file_controller", description="Clean temporary files", parameters={"action": "clean_temp"})]
        else:
            return [TaskStep(step_id=1, tool="open_app", description="Open temp folder", parameters={"app_name": "%temp%"})]
    elif "open" in g_lower or "kholo" in g_lower or "show" in g_lower or "dikhao" in g_lower:
        app = goal.split("open", 1)[-1].strip() if "open" in g_lower else goal.strip()
        return [TaskStep(step_id=1, tool="open_app", description=f"Open {app}", parameters={"app_name": app})]
    elif "volume" in g_lower or "brightness" in g_lower or "awaz" in g_lower:
        return [TaskStep(step_id=1, tool="computer_settings", description=goal, parameters={"action": "set", "description": goal})]
    elif "play" in g_lower or "chalao" in g_lower or "baja" in g_lower or "song" in g_lower or "gaana" in g_lower:
        song = goal.split("play", 1)[-1].strip() if "play" in g_lower else goal.strip()
        return [TaskStep(step_id=1, tool="youtube_video", description=f"Play {song}", parameters={"action": "play", "query": song})]
    elif any(w in g_lower for w in ["delete", "remove", "clean"]):
        return [TaskStep(step_id=1, tool="file_controller", description=goal, parameters={"action": "clean_temp"})]
    else:
        return [TaskStep(step_id=1, tool="deep_research", description=f"Research {goal}", parameters={"query": goal})]


def replan_remaining_steps(
    goal: str,
    completed_steps: List[Dict[str, Any]],
    failed_step: TaskStep,
    error_reason: str,
    alternative_strategy: str = "",
) -> List[TaskStep]:
    """
    Generate an updated plan for the remaining uncompleted portion of the goal.
    Excludes already finished steps and changes approach for the failed step.
    """
    completed_summary = "\n".join(
        f"  - Step {s.get('step_id')}: [{s.get('tool')}] {s.get('description')} (COMPLETED)"
        for s in completed_steps
    )
    prompt = (
        f"Goal: {goal}\n\n"
        f"Already successfully completed:\n{completed_summary if completed_summary else '  (none)'}\n\n"
        f"FAILED STEP: [{failed_step.tool}] {failed_step.description}\n"
        f"Failure Reason: {error_reason}\n"
        f"Recommended Alternative: {alternative_strategy}\n\n"
        "Create a REVISED plan for the REMAINING steps only. Do not repeat completed steps or the failed strategy."
    )

    try:
        return create_agent_plan(goal=goal, context=prompt)
    except Exception as e:
        logger.warning(f"[Planner] Replan generation failed: {e}")
        return []