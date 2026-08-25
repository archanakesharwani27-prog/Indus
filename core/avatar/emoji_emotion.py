# core/avatar/emoji_emotion.py
"""
INDUS Avatar System -- Emoji-to-Emotion Detector
Scans Gemini output text for emojis + keywords -> facial emotion state.
"""

import re
from typing import Optional, List, Tuple
from core.avatar.models import EmotionType

# ── Emoji → EmotionType ───────────────────────────────────────────────────────
EMOJI_EMOTION_MAP: dict = {
    # HAPPY
    '\U0001f60a': EmotionType.HAPPY, '\U0001f604': EmotionType.HAPPY,
    '\U0001f601': EmotionType.HAPPY, '\U0001f970': EmotionType.HAPPY,
    '\U0001f603': EmotionType.HAPPY, '\U0001f600': EmotionType.HAPPY,
    '\U0001f602': EmotionType.HAPPY, '\U0001f923': EmotionType.HAPPY,
    '\U0001f60b': EmotionType.HAPPY, '\U0001f642': EmotionType.HAPPY,
    '\U0001f638': EmotionType.HAPPY, '\U0001f44d': EmotionType.HAPPY,
    '\u2705':      EmotionType.HAPPY,
    # EXCITED
    '\U0001f60d': EmotionType.EXCITED, '\U0001f929': EmotionType.EXCITED,
    '\U0001f389': EmotionType.EXCITED, '\u2728':      EmotionType.EXCITED,
    '\U0001f525': EmotionType.EXCITED, '\u26a1':      EmotionType.EXCITED,
    '\U0001f4ab': EmotionType.EXCITED, '\U0001f31f': EmotionType.EXCITED,
    '\U0001f680': EmotionType.EXCITED, '\U0001f4a5': EmotionType.EXCITED,
    '\U0001f38a': EmotionType.EXCITED, '\U0001f3c6': EmotionType.EXCITED,
    '\U0001f4aa': EmotionType.EXCITED,
    # SAD
    '\U0001f622': EmotionType.SAD, '\U0001f62d': EmotionType.SAD,
    '\U0001f614': EmotionType.SAD, '\U0001f494': EmotionType.SAD,
    '\U0001f61e': EmotionType.SAD, '\U0001f63f': EmotionType.SAD,
    '\U0001f62a': EmotionType.SAD, '\U0001f613': EmotionType.SAD,
    # THINKING
    '\U0001f914': EmotionType.THINKING, '\U0001f4ad': EmotionType.THINKING,
    '\U0001f9d0': EmotionType.THINKING, '\U0001f928': EmotionType.THINKING,
    '\U0001f4a1': EmotionType.THINKING, '\U0001f9e0': EmotionType.THINKING,
    '\u23f3':     EmotionType.THINKING, '\U0001f50d': EmotionType.THINKING,
    # SURPRISED
    '\U0001f62e': EmotionType.SURPRISED, '\U0001f632': EmotionType.SURPRISED,
    '\U0001f92f': EmotionType.SURPRISED, '\U0001f631': EmotionType.SURPRISED,
    '\U0001f633': EmotionType.SURPRISED, '\U0001f640': EmotionType.SURPRISED,
    '\u2757':     EmotionType.SURPRISED,
    # ANGRY
    '\U0001f621': EmotionType.ANGRY, '\U0001f624': EmotionType.ANGRY,
    '\U0001f4a2': EmotionType.ANGRY, '\U0001f47f': EmotionType.ANGRY,
    '\U0001f620': EmotionType.ANGRY, '\U0001f92c': EmotionType.ANGRY,
    # CALM
    '\U0001f60c': EmotionType.CALM, '\U0001f64f': EmotionType.CALM,
    '\U0001f607': EmotionType.CALM, '\U0001f338': EmotionType.CALM,
    '\U0001f406': EmotionType.CALM,
    # CONFUSED
    '\U0001f615': EmotionType.CONFUSED, '\U0001f937': EmotionType.CONFUSED,
    '\U0001f926': EmotionType.CONFUSED, '\U0001f635': EmotionType.CONFUSED,
    '\U0001f636': EmotionType.CONFUSED, '\u2753':     EmotionType.CONFUSED,
    # CONCERNED
    '\U0001f630': EmotionType.CONCERNED, '\U0001f61f': EmotionType.CONCERNED,
    '\U0001f628': EmotionType.CONCERNED, '\U0001f626': EmotionType.CONCERNED,
    '\U0001f627': EmotionType.CONCERNED, '\u26a0\ufe0f': EmotionType.CONCERNED,
}

# Keyword triggers (lowercase substrings → emotion)
_KEYWORD_MAP: List[Tuple[List[str], EmotionType]] = [
    (["error", "fail", "crash", "broke", "problem", "issue", "warning"],
     EmotionType.CONCERNED),
    (["sorry", "apologize", "mistake", "oops", "unfortunately"],
     EmotionType.SAD),
    (["great", "excellent", "perfect", "done", "complete", "success",
      "theek", "ho gaya", "kar diya", "shukriya"],
     EmotionType.HAPPY),
    (["thinking", "analyzing", "checking", "wait", "soch", "dekh",
      "let me", "hmm", "processing"],
     EmotionType.THINKING),
    (["wow", "incredible", "awesome", "fantastic", "amazing",
      "superb", "bahut accha", "zabardast"],
     EmotionType.EXCITED),
    (["really?", "seriously?", "no way", "kya?", "sach mein?"],
     EmotionType.SURPRISED),
]

_EMOJI_RE = re.compile(
    "[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF"
    "\U00002600-\U000027BF\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF]+",
    flags=re.UNICODE
)


def detect_emotion_from_text(text: str) -> Optional[EmotionType]:
    """
    Scan Gemini output text for emojis + keywords.
    Returns EmotionType if detected, None to keep current emotion.
    """
    if not text:
        return None

    # 1. Emoji scan (priority)
    for emoji_str in _EMOJI_RE.findall(text):
        for ch in emoji_str:
            emo = EMOJI_EMOTION_MAP.get(ch)
            if emo:
                return emo

    # 2. Keyword scan
    lower = text.lower()
    for keywords, emotion in _KEYWORD_MAP:
        if any(kw in lower for kw in keywords):
            return emotion

    return None


def strip_emojis(text: str) -> str:
    """Remove all emojis from text for cleaner phoneme extraction."""
    return _EMOJI_RE.sub('', text).strip()
