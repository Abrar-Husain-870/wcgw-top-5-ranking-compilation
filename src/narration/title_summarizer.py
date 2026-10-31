"""
Title Summarizer module for Top 5 Ranking Shorts.
Condenses verbose Reddit post titles into punchy 2-3 word ranking labels
plus an emoji (e.g. 'Diving goes wrong 😭', 'Cake is cooked 🤣', 'Poor grandy 😂').
Uses Groq LLM when GROQ_API_KEY is configured, with a robust local regex fallback.
"""
from __future__ import annotations

import re
import random
from typing import Optional

import config
from src.logger import logger


FALLBACK_EMOJIS = ["💀", "😭", "🤣", "😨", "☠️", "🤦‍♂️", "💥", "😂"]

KEYWORD_EMOJI_MAP = {
    "pool": "🏊‍♂️",
    "water": "🌊",
    "dive": "🏊‍♂️",
    "diving": "🏊‍♂️",
    "car": "🚗",
    "drive": "🚗",
    "driving": "🚗",
    "bike": "🚲",
    "skate": "🛹",
    "cake": "🎂",
    "dog": "🐶",
    "cat": "🐱",
    "fire": "🔥",
    "jump": "🦘",
    "fall": "😭",
    "falling": "😭",
    "fail": "💀",
    "cook": "🍳",
    "cooked": "💀",
}


def _local_summarize_fallback(title: str) -> str:
    """Local heuristic fallback that truncates and formats a title to max 3 words + emoji."""
    # 1. Remove brackets, tags, urls, punctuation
    cleaned = re.sub(r'\[.*?\]|\(.*?\)|<.*?>', '', title)
    cleaned = re.sub(r'https?://\S+|www\.\S+', '', cleaned)
    cleaned = re.sub(r'r/\w+|u/\w+', '', cleaned)
    cleaned = re.sub(r'[^a-zA-Z0-9\s]', ' ', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()

    words = cleaned.split()
    if not words:
        return f"Fail moment {random.choice(FALLBACK_EMOJIS)}"

    # Determine relevant emoji
    matched_emoji = None
    title_lower = title.lower()
    for kw, em in KEYWORD_EMOJI_MAP.items():
        if kw in title_lower:
            matched_emoji = em
            break
    if not matched_emoji:
        matched_emoji = random.choice(FALLBACK_EMOJIS)

    # Filter out common filler words from the start
    stop_words = {
        "a", "an", "the", "when", "how", "what", "to", "in", "on", "of", "and",
        "this", "that", "he", "she", "they", "is", "was", "are", "were", "my",
        "his", "her", "trying", "tries", "just", "got", "gets", "getting"
    }
    meaningful_words = [w for w in words if w.lower() not in stop_words]
    if len(meaningful_words) < 2:
        meaningful_words = words

    # Take at most 3 words
    selected_words = meaningful_words[:3]
    # Capitalize the first word and keep others lowercase or titlecase
    result_text = " ".join(selected_words).capitalize()

    return f"{result_text} {matched_emoji}"


def summarize_ranking_title(title: str) -> str:
    """
    Summarizes a Reddit title to at most 3 words followed by 1 emoji.
    Uses Groq LLM if GROQ_API_KEY is available, otherwise uses local fallback.
    """
    groq_key = getattr(config, "GROQ_API_KEY", "") or ""
    if not groq_key:
        logger.debug("GROQ_API_KEY not configured. Using local title summarizer.")
        return _local_summarize_fallback(title)

    try:
        from groq import Groq
        client = Groq(api_key=groq_key)
        system_prompt = (
            "You are a viral YouTube Shorts editor. Your task is to summarize Reddit fail titles "
            "into a punchy, humorous ranking label.\n"
            "RULES:\n"
            "1. Output MUST be MAXIMUM 3 WORDS followed by EXACTLY ONE relevant emoji (e.g. 💀, 😭, 🤣, 😨, ☠️).\n"
            "2. Keep it punchy, funny, and direct (e.g., 'Cake is cooked 🤣', 'Diving goes wrong 😭', 'Poor grandy 😂', 'Falling from heaven 💀').\n"
            "3. Do NOT include numbers, quotes, prefixes, or explanations.\n"
            "4. Output ONLY the 1-3 words and 1 emoji."
        )
        user_prompt = f"Reddit Title: {title}"

        candidate_models = ["openai/gpt-oss-20b", "openai/gpt-oss-120b", "qwen/qwen3.8-27b", "llama-3.3-70b-versatile"]
        output_text = ""
        for m in candidate_models:
            try:
                response = client.chat.completions.create(
                    model=m,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.3,
                    max_tokens=25
                )
                output_text = response.choices[0].message.content.strip().strip('"').strip("'")
                if output_text:
                    break
            except Exception as me:
                err_s = str(me).lower()
                if "404" in err_s or "model_not_found" in err_s:
                    continue
                raise me
        
        # Validate that output is <= 3 words (excluding emoji)
        # Separate emojis from words
        tokens = output_text.split()
        if len(tokens) > 4:  # 3 words + 1 emoji
            # Truncate
            output_text = " ".join(tokens[:3])
            if not any(e in output_text for e in FALLBACK_EMOJIS):
                output_text += f" {random.choice(FALLBACK_EMOJIS)}"

        logger.info(f"Groq Title Summarized: '{title[:40]}...' -> '{output_text}'")
        return output_text

    except Exception as e:
        logger.warning(f"Groq title summarization failed: {e}. Using local fallback.")
        return _local_summarize_fallback(title)
