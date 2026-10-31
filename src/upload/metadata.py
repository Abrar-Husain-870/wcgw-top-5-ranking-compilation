import re
import random
from typing import List, Dict, Optional
import config
from src.logger import logger
from src.reddit.models import RedditPost

# Default Lists of Tags and Hashtags
EVERGREEN_TAGS = [
    "shorts", "youtubeshorts", "viral", "trending", "whatcouldgowrong",
    "wcgw", "unexpected", "accidentalslapstick", "slapstick", "instantkarma", "instantregret", "fail",
    "fails", "funny videos", "reddit", "fyp", "comedy", "humor"
]

DEFAULT_TRENDING_TAGS = [
    "whatcouldgowrong", "wcgw", "unexpected", "accidentalslapstick", "slapstick", "instantkarma", "instantregret",
    "fail", "fails", "viral", "fyp", "shorts", "comedy"
]

EVERGREEN_HASHTAGS = [
    "#Shorts", "#WhatCouldGoWrong", "#Unexpected", "#AccidentalSlapStick", "#Slapstick", "#InstantKarma",
    "#InstantRegret", "#Fail", "#Fails", "#Funny", "#Reddit", "#Comedy", "#Viral"
]

# Curiosity-driven title templates if LLM title is missing or invalid
TITLE_TEMPLATES = [
    "This is way too relatable...",
    "Why is this actually true?",
    "I feel personally called out by this...",
    "Who else does this every single time?",
    "This made me laugh way too hard!",
    "Expectation vs Reality is crazy...",
    "I wasn't expecting that ending!",
    "This is surprisingly wholesome...",
    "My last brain cell trying to figure this out...",
    "Wait for the end, it gets better..."
]

# Call to Action (CTA) list
CTA_LIST = [
    "Who can relate to this? Let me know below!",
    "Tag a friend who is exactly like this!",
    "Has this ever happened to you? Tell me below!",
    "Share your favorite part in the comments!",
    "Rate this meme from 1 to 10 in the comments!"
]

# Mapping human-readable categories to YouTube category IDs
CATEGORY_MAPPING = {
    "comedy": "23",
    "entertainment": "24",
    "education": "27",
    "people & blogs": "22",
    "people": "22",
    "blogs": "22"
}

def clean_title(title: str) -> str:
    """Clean title to remove quotes, excessive caps, and enforce all-age guidelines."""
    # Remove surrounding quotes
    title = title.strip('\'"“”')
    # If title is in ALL CAPS, convert to Title Case
    if title.isupper():
        title = title.title()
    # Remove double spaces
    title = re.sub(r'\s+', ' ', title)
    return title.strip()

def generate_optimized_metadata(
    post: RedditPost,
    narration: str,
    llm_title: str = "",
    llm_hook: str = "",
    llm_summary: str = "",
    llm_category: str = "",
    llm_content_tags: List[str] = None
) -> Dict[str, any]:
    """
    Generates YouTube/Shorts metadata meeting engagement and quality guidelines.
    Uses LLM outputs if available, otherwise falls back to robust local rules.
    """
    logger.info("Generating optimized metadata for Short...")
    
    # ── 1. TITLE GENERATION ─────────────────────────────────────────────────
    title = ""
    if llm_title:
        title = clean_title(llm_title)
        
    # If Curator Mode (video memes/fails), the original post title is the best title.
    if config.CURATOR_MODE:
        title = clean_title(post.title)
        # Use full Reddit title cleanly up to YouTube's 100 character limit
        if len(title) > 95:
            title = title[:92].rsplit(' ', 1)[0] + "..."
    else:
        # If LLM title is missing or doesn't meet size requirements (40-70 chars preferred)
        if not title or len(title) < 30 or len(title) > 85:
            # Generate dynamic curiosity title based on subreddit/keywords
            template = random.choice(TITLE_TEMPLATES)
            sub_name = post.subreddit.replace("wholesomememes", "Wholesome").replace("tifu", "TIFU")
            candidate = f"r/{sub_name} | {template}"
            
            if 40 <= len(candidate) <= 75:
                title = candidate
            else:
                title = template

        # Enforce hard YouTube Title limit (100 chars max, cropped to 75 for Shorts optimal views)
        title = title[:75]
    
    # ── 2. DESCRIPTION GENERATION ───────────────────────────────────────────
    # Description Hook (1-2 lines)
    hook = llm_hook.strip() if llm_hook else f"This story from r/{post.subreddit} is absolutely wild."
    if not hook.endswith((".", "!", "?")):
        hook += "..."
        
    # Summary of post (1-2 sentences)
    summary = llm_summary.strip() if llm_summary else ""
    if not summary:
        if narration:
            # fallback: use first sentence of narration
            sentences = re.split(r'(?<=[.!?])\s+', narration)
            if sentences and sentences[0]:
                summary = sentences[0]
                if len(sentences) > 1 and len(summary) < 60:
                    summary += " " + sentences[1]
        if not summary:
            summary = post.title
                
    # Mentions
    mentions_str = ""
    config_mentions = getattr(config, "METADATA_MENTIONS", "")
    if config_mentions:
        mentions_list = [m.strip() for m in config_mentions.split(",") if m.strip()]
        mentions_str = " ".join(mentions_list) + "\n\n"
        
    # AI Narration Disclaimer
    if config.CURATOR_MODE:
        disclaimer = getattr(config, "METADATA_DISCLAIMER", "Curated funny video meme from Reddit.")
    else:
        disclaimer = getattr(config, "METADATA_DISCLAIMER", "Narration is an AI-generated retelling and commentary of this story.")
    
    # Call to Action (CTA)
    cta = random.choice(CTA_LIST)
    
    # Build description body
    if config.CURATOR_MODE:
        desc_parts = [
            summary,
            "",
            f"Curated from r/{post.subreddit}.",
            f"Original Post Title: {post.title}",
            f"Original Creator: u/{post.author}",
            "",
            disclaimer,
            "",
            cta
        ]
    else:
        desc_parts = [
            hook,
            "",
            summary,
            "",
            f"Retold from r/{post.subreddit}.",
            f"Original Post Title: {post.title}",
            "",
            disclaimer,
            "",
            cta
        ]
    
    description_text = "\n".join(desc_parts).strip()
    if mentions_str:
        description_text = mentions_str + description_text
        
    # ── 3. HASHTAGS GENERATION ──────────────────────────────────────────────
    # Pick 3-8 hashtags
    hashtag_set = set(EVERGREEN_HASHTAGS)
    
    # Add content-specific hashtag
    sub_tag = f"#{post.subreddit}"
    hashtag_set.add(sub_tag)
    
    # Add tags parsed from LLM if any
    if llm_content_tags:
        for t in llm_content_tags:
            cleaned_tag = f"#{t.replace(' ', '').replace('#', '')}"
            if len(cleaned_tag) > 2:
                hashtag_set.add(cleaned_tag)
                
    # Select a subset of 4-6 hashtags randomly
    selected_hashtags = random.sample(list(hashtag_set), min(len(hashtag_set), 6))
    
    # Ensure #Shorts is always present
    if "#Shorts" not in selected_hashtags:
        selected_hashtags.insert(0, "#Shorts")
        
    hashtags_str = " ".join(selected_hashtags[:8])
    description_text += f"\n\n{hashtags_str}"

    # ── 4. TAGS GENERATION ──────────────────────────────────────────────────
    tags_pool = set(EVERGREEN_TAGS)
    
    # Load trending tags from config/env
    trending_config = getattr(config, "METADATA_TRENDING_TAGS", "")
    if trending_config:
        config_trending = [t.strip().lower() for t in trending_config.split(",") if t.strip()]
        tags_pool.update(config_trending)
    else:
        tags_pool.update(DEFAULT_TRENDING_TAGS)
        
    # Add content-specific tags
    tags_pool.add(post.subreddit.lower())
    tags_pool.add(f"r/{post.subreddit.lower()}")
    tags_pool.add("reddit stories")
    tags_pool.add("reddit narration")
    
    if llm_content_tags:
        tags_pool.update([t.lower().strip() for t in llm_content_tags])
        
    final_tags = list(tags_pool)[:20]  # Max 20 tags to avoid keyword stuffing

    # ── 5. CATEGORY ID SELECTION ────────────────────────────────────────────
    category_id = "22"  # default: People & Blogs
    if llm_category:
        cat_clean = llm_category.lower().strip()
        if cat_clean in CATEGORY_MAPPING:
            category_id = CATEGORY_MAPPING[cat_clean]
            
    logger.info(f"Metadata generated successfully:")
    logger.info(f"   Optimized Title: {title}")
    logger.info(f"   Category ID: {category_id}")
    logger.info(f"   Tags Count: {len(final_tags)}")

    return {
        "title": title,
        "description": description_text,
        "tags": final_tags,
        "category_id": category_id
    }


def generate_compilation_metadata(clips_data: list[dict]) -> dict:
    """
    Generates high-CTR metadata tailored for YouTube Shorts Top 5 countdown compilations.
    Includes timestamps in description for each clip.
    """
    rank_1_title = ""
    for item in clips_data:
        if item.get("rank") == 1:
            rank_1_title = item.get("title", "")
            break
    if not rank_1_title and clips_data:
        rank_1_title = clips_data[-1].get("title", "")

    title = ""
    # Try dynamic AI-generated title via Groq
    if getattr(config, "GROQ_API_KEY", None):
        try:
            from groq import Groq
            client = Groq(api_key=config.GROQ_API_KEY)
            clips_summary = ", ".join([f"#{c.get('rank', idx+1)} {c.get('title', '')}" for idx, c in enumerate(clips_data)])
            completion = client.chat.completions.create(
                model="openai/gpt-oss-20b",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a YouTube Shorts viral marketing expert. Generate ONE unique, high-CTR, clicky compilation title "
                            "under 75 characters for a fail countdown video. Include 1 emoji and '#Shorts'. "
                            "Make it curious, funny, or shocking. Output ONLY the raw title text without quotes or explanation."
                        )
                    },
                    {
                        "role": "user",
                        "content": f"The countdown clips from #5 to #1 grand finale are: {clips_summary}. Climax clip is: {rank_1_title}."
                    }
                ],
                temperature=0.7,
                max_tokens=60,
                timeout=5
            )
            raw_ai_title = completion.choices[0].message.content.strip().strip('"\'')
            if raw_ai_title and 20 <= len(raw_ai_title) <= 90:
                if "#Shorts" not in raw_ai_title and "#shorts" not in raw_ai_title:
                    raw_ai_title += " #Shorts"
                title = raw_ai_title
                logger.info(f"AI generated compilation title: '{title}'")
        except Exception as e:
            logger.debug(f"AI compilation title generation fallback: {e}")

    # Fallback to dynamic template selection featuring the actual #1 clip name
    if not title:
        r1_display = rank_1_title.strip() if rank_1_title else "The Finale"
        title_options = [
            f"Ranking Top 5 Fails (#1: {r1_display}) 😭 #Shorts",
            f"Top 5 Instant Regrets (#1: {r1_display}) 💀 #Shorts",
            f"Wait For #1... Top 5 Fails Ranked 😭 #Shorts",
            f"Top 5 What Could Go Wrong Moments (#1 Was Wild) 🤯 #Shorts",
            f"Ranking 5 Fails That Hurt To Watch (#1: {r1_display}) 💀 #Shorts",
            f"Top 5 Funniest Fails of the Week (#1 Winner) 🏆 #Shorts",
            f"Ranking Top 5 Instant Regrets (#1 Was Cooking) 😭 #Shorts",
            f"Top 5 Dumbest Decisions Ranked (#1 is Crazy) 💀 #Shorts",
            f"Ranking The Best Fails Ever (#1: {r1_display}) 😱 #Shorts",
            f"5 People Having A Worse Day Than You (#1 is Wild) 😭 #Shorts",
            f"Top 5 Instant Karma & Fail Moments (#{r1_display}) 💀 #Shorts",
            f"Ranking Top 5 Fails (#1 Did Not Expect That) 😂 #Shorts",
            f"Top 5 Fails Caught On Camera (#1: {r1_display}) 💀 #Shorts",
            f"Ranking Fails That Defy All Logic (#1 Winner) 😭 #Shorts",
            f"Top 5 Times Things Went Completely Wrong (#1) 🤯 #Shorts",
        ]
        title = random.choice(title_options)

    # Build description with timestamps
    description_lines = [
        "Which one was the craziest? Rate them 1-10 in the comments! 👇\n",
        "TIMESTAMPS:"
    ]

    curr_time = 0.0
    for item in clips_data:
        r = item.get("rank", 1)
        dur = item.get("duration", 8.0)
        t_label = item.get("title", f"Clip #{r}")
        mins = int(curr_time // 60)
        secs = int(curr_time % 60)
        time_str = f"{mins}:{secs:02d}"
        if r == 1:
            description_lines.append(f"{time_str} - #{r} {t_label} (Grand Finale)")
        else:
            description_lines.append(f"{time_str} - #{r} {t_label}")
        curr_time += dur

    description_lines.append("\nCurated funniest moments from Reddit.")
    description_lines.append(getattr(config, "METADATA_DISCLAIMER", "Curated clips from r/Whatcouldgowrong, r/Unexpected, and r/AccidentalSlapStick."))
    description_lines.append("\n#Shorts #Ranking #Fails #WhatCouldGoWrong #InstantRegret #Viral #Comedy")

    description = "\n".join(description_lines)

    tags = [
        "shorts", "ranking", "top 5", "top 5 fails", "fails", "fail compilation",
        "whatcouldgowrong", "wcgw", "unexpected", "instantregret", "instantkarma",
        "viral", "trending", "comedy", "funny videos", "reddit"
    ]

    return {
        "title": title,
        "description": description,
        "tags": tags,
        "category_id": "23"  # 23 = Comedy
    }

