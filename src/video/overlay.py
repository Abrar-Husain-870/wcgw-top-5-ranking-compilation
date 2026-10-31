import re
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

import config
from src.logger import logger
from src.reddit.models import RedditPost


def _wrap_text(text: str, draw: ImageDraw.ImageDraw, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    """Wrap text to fit within a maximum width in pixels."""
    words = text.split()
    lines = []
    current_line = []
    
    for word in words:
        current_line.append(word)
        line_str = " ".join(current_line)
        # Get width of current line
        bbox = draw.textbbox((0, 0), line_str, font=font)
        w = bbox[2] - bbox[0]
        
        if w > max_width:
            if len(current_line) == 1:
                # Word itself is too long, force split it
                lines.append(line_str)
                current_line = []
            else:
                current_line.pop()
                lines.append(" ".join(current_line))
                current_line = [word]
                
    if current_line:
        lines.append(" ".join(current_line))
        
    return lines


def generate_reddit_card(post: RedditPost) -> Path:
    """
    Generate a beautiful dark mode Reddit post card overlay.
    Returns the path to the saved transparent PNG image.
    """
    output_path = config.OUTPUT_DIR / "reddit_card.png"
    
    # ── Dimensions & Padding ─────────────────────────────────
    card_width = 900
    padding = 40
    
    # Fonts loading with fallbacks
    try:
        # Try loading standard windows / unix sans fonts
        font_title = ImageFont.truetype("arialbd.ttf", 36)
        font_meta = ImageFont.truetype("arial.ttf", 24)
        font_meta_bold = ImageFont.truetype("arialbd.ttf", 24)
    except Exception:
        try:
            font_title = ImageFont.truetype("DejaVuSans-Bold.ttf", 36)
            font_meta = ImageFont.truetype("DejaVuSans.ttf", 24)
            font_meta_bold = ImageFont.truetype("DejaVuSans-Bold.ttf", 24)
        except Exception:
            # Absolute fallback
            font_title = ImageFont.load_default()
            font_meta = ImageFont.load_default()
            font_meta_bold = ImageFont.load_default()

    # Pre-render wrap to calculate dynamic height
    temp_img = Image.new("RGBA", (card_width, 100))
    temp_draw = ImageDraw.Draw(temp_img)
    
    max_text_width = card_width - (padding * 2)
    wrapped_title = _wrap_text(post.title, temp_draw, font_title, max_text_width)
    
    # Title height estimation
    line_spacing = 8
    title_height = 0
    for line in wrapped_title:
        bbox = temp_draw.textbbox((0, 0), line, font=font_title)
        h = bbox[3] - bbox[1]
        title_height += h + line_spacing
    title_height = max(title_height - line_spacing, 40)
    
    # Header: 60px, Footer: 50px, Padding/Spacing: 100px
    card_height = 60 + title_height + 50 + (padding * 2) + 20
    
    # ── Draw Card ────────────────────────────────────────────
    # Transparent canvas
    canvas = Image.new("RGBA", (card_width, card_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    
    # Colors
    bg_color = (26, 26, 27, 240)        # Reddit Dark Mode Background (#1A1A1B, 94% opaque)
    reddit_orange = (255, 69, 0, 255)   # #FF4500
    text_white = (255, 255, 255, 255)   # #FFFFFF
    text_gray = (120, 124, 126, 255)    # #787C7E
    border_gray = (52, 53, 54, 255)     # #343536
    
    # Draw rounded background
    draw.rounded_rectangle(
        [(0, 0), (card_width, card_height)],
        radius=20,
        fill=bg_color,
        outline=border_gray,
        width=2
    )
    
    # 1. Header (Subreddit Badge, Subreddit Name, Author, Timestamp)
    y_cursor = padding
    
    if config.OVERLAY_PROFILE_ICON:
        # Draw circular orange badge placeholder
        badge_radius = 20
        badge_center = (padding + badge_radius, y_cursor + badge_radius)
        draw.ellipse(
            [(badge_center[0] - badge_radius, badge_center[1] - badge_radius),
             (badge_center[0] + badge_radius, badge_center[1] + badge_radius)],
            fill=reddit_orange
        )
        # Draw small 'r/' text on badge
        draw.text(
            (badge_center[0] - 8, badge_center[1] - 12),
            "r",
            font=font_meta_bold,
            fill=text_white
        )
        x_cursor = padding + (badge_radius * 2) + 15
    else:
        x_cursor = padding
        
    # Subreddit Name
    sub_tag = f"r/{post.subreddit}" if config.OVERLAY_SUBREDDIT_TAG else "r/Reddit"
    draw.text((x_cursor, y_cursor + 6), sub_tag, font=font_meta_bold, fill=text_white)
    
    # Get width of subreddit tag to align u/author
    sub_bbox = draw.textbbox((0, 0), sub_tag, font=font_meta_bold)
    sub_w = sub_bbox[2] - sub_bbox[0]
    
    # Author and Meta info
    meta_text = f" • Posted by u/{post.author}"
    draw.text(
        (x_cursor + sub_w + 5, y_cursor + 6),
        meta_text,
        font=font_meta,
        fill=text_gray
    )
    
    y_cursor += 65  # Advance below header
    
    # 2. Post Title
    for line in wrapped_title:
        draw.text((padding, y_cursor), line, font=font_title, fill=text_white)
        # Compute height of line
        bbox = draw.textbbox((0, 0), line, font=font_title)
        h = bbox[3] - bbox[1]
        y_cursor += h + line_spacing
        
    y_cursor += 15  # Spacing before footer
    
    # Draw simple thin separator line
    draw.line(
        [(padding, y_cursor), (card_width - padding, y_cursor)],
        fill=border_gray,
        width=1
    )
    y_cursor += 15
    
    # 3. Footer (Upvotes & Comments counts)
    # Formats count like 1.2k if > 1000
    def format_count(num: int) -> str:
        if num >= 1000:
            return f"{num / 1000:.1f}k"
        return str(num)
        
    stats_text = f"▲ {format_count(post.score)}  |  💬 {format_count(post.num_comments)} Comments"
    draw.text((padding, y_cursor), stats_text, font=font_meta_bold, fill=text_gray)
    
    # Save the card image
    canvas.save(output_path, "PNG")
    logger.info(f"Reddit card overlay generated at {output_path} ({card_width}x{card_height})")
    return output_path


def split_caption_for_landscape(title: str) -> tuple[str, str | None]:
    """
    Intelligently splits a title into (top_text, bottom_text) for landscape videos.
    If the title is short, keeps it as a single punchy top title and returns (top_text, None).
    """
    clean = re.sub(r'\s+', ' ', title).strip()
    words = clean.split()
    
    # If title is short (<= 7 words and <= 38 characters), keep together on top
    if len(words) <= 7 and len(clean) <= 38:
        return clean, None
        
    # Check for strong sentence/clause delimiters: ".", "?", "!", ";", " - ", " | "
    for delim in [". ", "? ", "! ", " - ", " | ", "; "]:
        if delim in clean:
            parts = clean.split(delim, 1)
            p1, p2 = parts[0].strip(), parts[1].strip()
            if delim.strip() in [".", "?", "!"]:
                p1 += delim.strip()
            if len(p1) >= 8 and len(p2) >= 8:
                return p1, p2
                
    # Check for secondary punctuation like commas
    if ", " in clean:
        parts = clean.split(", ", 1)
        p1, p2 = parts[0].strip(), parts[1].strip()
        if len(p1) >= 10 and len(p2) >= 10:
            return p1, p2
            
    # Check for natural conjunction split points near middle
    conjunctions = [" while ", " when ", " but ", " until ", " then ", " and ", " because "]
    mid_idx = len(clean) // 2
    best_conj = None
    best_dist = 999
    for conj in conjunctions:
        idx = clean.lower().find(conj)
        while idx != -1:
            dist = abs(idx - mid_idx)
            if dist < best_dist and idx > 10 and (len(clean) - idx) > 10:
                best_dist = dist
                best_conj = (idx, conj)
            idx = clean.lower().find(conj, idx + len(conj))
            
    if best_conj and best_dist < len(clean) * 0.35:
        idx, conj = best_conj
        p1 = clean[:idx].strip()
        p2 = clean[idx:].strip()
        return p1, p2
        
    # Fallback: split evenly by words
    mid_word = len(words) // 2
    p1 = " ".join(words[:mid_word])
    p2 = " ".join(words[mid_word:])
    return p1, p2


def generate_creator_caption_banner(
    text: str,
    max_width: int = 1000,
    min_width: int = 840,
    font_size: int = 0,
    is_bottom: bool = False,
    is_vertical: bool = False,
    filename: str = "top_caption.png"
) -> Path:
    """
    Generate an impactful, viral creator-style caption banner.
    Dynamically scales font size and container width to eliminate dead blank space.
    """
    output_path = config.OUTPUT_DIR / filename
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    clean_text = re.sub(r'\s+', ' ', text).strip()
    if not clean_text:
        return output_path

    # Determine dynamic font size based on text length and placement
    if font_size <= 0:
        if is_vertical:
            font_size = 42
            min_width = 650
        elif is_bottom:
            font_size = 48 if len(clean_text) <= 35 else 42
            min_width = 780
        else:
            # Top banner for horizontal/square:
            if len(clean_text) <= 26:
                font_size = 56  # Bold, punchy text for short titles
                min_width = 820
            elif len(clean_text) <= 48:
                font_size = 48
                min_width = 800
            else:
                font_size = 42
                min_width = 760

    # Load bold fonts
    font = None
    for font_path in [
        "C:/Windows/Fonts/ariblk.ttf",      # Arial Black (extra bold)
        "C:/Windows/Fonts/arialbd.ttf",     # Arial Bold
        "C:/Windows/Fonts/segoeuib.ttf",    # Segoe UI Bold
        "arialbd.ttf",
        "DejaVuSans-Bold.ttf"
    ]:
        try:
            font = ImageFont.truetype(font_path, font_size)
            break
        except Exception:
            continue
    if font is None:
        font = ImageFont.load_default()

    # Pre-render dummy image for text measurement
    dummy = Image.new("RGBA", (max_width, 100))
    d = ImageDraw.Draw(dummy)
    
    # Calculate wrapped lines
    padding_x = 48
    padding_y = 28
    line_spacing = 14
    max_text_w = max_width - (padding_x * 2)
    lines = _wrap_text(clean_text, d, font, max_text_w)
    if not lines:
        lines = [clean_text]
    full_text = "\n".join(lines)
        
    # Measure whole multiline text block accurately using Pillow's multiline_textbbox
    mb = d.multiline_textbbox((0, 0), full_text, font=font, spacing=line_spacing, align="center")
    text_w = int(mb[2] - mb[0])
    text_h = int(mb[3] - mb[1])
    
    # Proportional banner width to balance and fill upper/lower zones
    banner_w = min(max_width, max(min_width, text_w + (padding_x * 2)))
    banner_h = text_h + (padding_y * 2)
    
    canvas = Image.new("RGBA", (banner_w, banner_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    
    # Clean, vibrant white card container with rounded corners and subtle crisp border
    bg_color = (255, 255, 255, 255)
    border_color = (212, 215, 222, 255)
    draw.rounded_rectangle(
        [(0, 0), (banner_w - 1, banner_h - 1)],
        radius=24,
        fill=bg_color,
        outline=border_color,
        width=2
    )
    
    # Draw centered text lines with razor-sharp black text (offset by mb[0], mb[1] for exact centering)
    text_x = int((banner_w - text_w) // 2 - mb[0])
    text_y = int((banner_h - text_h) // 2 - mb[1])
    text_color = (12, 12, 16, 255)  # Deep bold black
    
    draw.multiline_text(
        (text_x, text_y),
        full_text,
        font=font,
        fill=text_color,
        align="center",
        spacing=line_spacing
    )
        
    canvas.save(output_path, "PNG")
    logger.info(f"Caption banner '{filename}' generated at {output_path} ({banner_w}x{banner_h}, font_size={font_size})")
    return output_path


# Backward compatibility alias
generate_top_caption_banner = generate_creator_caption_banner


def generate_ranking_compilation_overlay(
    active_rank: int,
    total_ranks: int = 5,
    rank_titles: dict[int, str] = None,
    header_text: str = "",
    filename: str = "ranking_overlay.png"
) -> Path:
    """
    Generates a viral ranking list overlay matching @Top6-Ranks aesthetic:
    - Top Header: 'Ranking Best [Accent Word]' with bold white and red text and black outline.
    - Left Ranking List: Numbers 1. to 5. with distinct colors and black outline.
    - Revealed Titles: Shows 3-word title + emoji for ranks that have been shown,
      with the currently playing rank prominently highlighted.
    """
    output_path = config.OUTPUT_DIR / filename
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if rank_titles is None:
        rank_titles = {}

    canvas = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    d = ImageDraw.Draw(canvas)

    # 1. Resolve Fonts
    font_bold_candidates = [
        "C:/Windows/Fonts/ariblk.ttf",       # Arial Black
        "C:/Windows/Fonts/impact.ttf",       # Impact
        "C:/Windows/Fonts/arialbd.ttf",      # Arial Bold
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "DejaVuSans-Bold.ttf",
        "arialbd.ttf"
    ]
    emoji_font_candidates = [
        "C:/Windows/Fonts/seguiemj.ttf",      # Segoe UI Emoji
        "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
        "seguiemj.ttf"
    ]

    f_head = None
    f_num = None
    f_txt = None
    f_emj = None

    for f_path in font_bold_candidates:
        try:
            f_head = ImageFont.truetype(f_path, 58)
            f_num = ImageFont.truetype(f_path, 50)
            f_txt = ImageFont.truetype(f_path, 44)
            break
        except Exception:
            continue

    if f_head is None:
        f_head = ImageFont.load_default()
        f_num = ImageFont.load_default()
        f_txt = ImageFont.load_default()

    for e_path in emoji_font_candidates:
        try:
            f_emj = ImageFont.truetype(e_path, 44)
            break
        except Exception:
            continue

    # 2. Draw Top Header: "Ranking Best Fails"
    if not header_text:
        header_text = getattr(config, "RANKING_HEADER_TEXT", "Ranking Best Fails")

    # Split into main text and accent text (last 1-2 words in red)
    header_words = header_text.strip().split()
    if len(header_words) > 1:
        # e.g. "Ranking Best" and "Fails"
        main_header = " ".join(header_words[:-1]) + " "
        accent_header = header_words[-1]
    else:
        main_header = header_text + " "
        accent_header = ""

    head_y = 140
    try:
        w_main = d.textlength(main_header, font=f_head)
        w_acc = d.textlength(accent_header, font=f_head) if accent_header else 0
        tot_w = w_main + w_acc
        start_x = int((1080 - tot_w) // 2)

        d.text(
            (start_x, head_y),
            main_header,
            font=f_head,
            fill=(255, 255, 255, 255),
            stroke_width=7,
            stroke_fill=(0, 0, 0, 255)
        )
        if accent_header:
            d.text(
                (start_x + int(w_main), head_y),
                accent_header,
                font=f_head,
                fill=(255, 34, 34, 255),  # Vibrant Red
                stroke_width=7,
                stroke_fill=(0, 0, 0, 255)
            )
    except Exception as e:
        logger.warning(f"Error drawing header text: {e}")

    # 3. Draw Ranking List on Left Side
    rank_colors = {
        1: (255, 229, 0, 255),   # Yellow/Gold
        2: (255, 255, 255, 255), # White
        3: (255, 149, 0, 255),   # Orange
        4: (255, 255, 255, 255), # White
        5: (255, 42, 42, 255),   # Red
        6: (255, 42, 42, 255),   # Red
    }

    start_y = 290
    spacing_y = 105
    left_x = 90

    for r in range(1, total_ranks + 1):
        curr_y = start_y + (r - 1) * spacing_y
        is_active = (r == active_rank)

        # Draw rank number: "1." or "5."
        num_str = f"{r}. "
        base_color = rank_colors.get(r, (255, 255, 255, 255))
        stroke_w = 7 if is_active else 5

        d.text(
            (left_x, curr_y),
            num_str,
            font=f_num,
            fill=base_color,
            stroke_width=stroke_w,
            stroke_fill=(0, 0, 0, 255)
        )
        try:
            num_w = int(d.textlength(num_str, font=f_num))
        except Exception:
            num_w = 70

        # In countdown mode (5 -> 1), titles are revealed for ranks >= active_rank
        # (or if rank_titles has this rank explicitly revealed)
        show_title = (r >= active_rank) and (r in rank_titles)

        if show_title:
            title_str = rank_titles[r]
            parts = title_str.rsplit(" ", 1)
            txt_part = parts[0]
            emj_part = parts[1] if len(parts) > 1 else ""

            # Highlight active rank with brighter/bold text
            text_color = (255, 255, 255, 255)
            txt_stroke = 6 if is_active else 5

            d.text(
                (left_x + num_w, curr_y),
                txt_part,
                font=f_txt,
                fill=text_color,
                stroke_width=txt_stroke,
                stroke_fill=(0, 0, 0, 255)
            )

            if emj_part and f_emj:
                try:
                    txt_w = int(d.textlength(txt_part, font=f_txt))
                    d.text(
                        (left_x + num_w + txt_w + 12, curr_y),
                        emj_part,
                        font=f_emj,
                        fill=(255, 255, 255, 255),
                        embedded_color=True
                    )
                except Exception:
                    pass

    canvas.save(output_path, "PNG")
    logger.info(f"Ranking compilation overlay generated at {output_path} (active rank #{active_rank})")
    return output_path

