#!/usr/bin/env python3
"""
Integration test for Top 5 Ranking Compilation Mode:
1. Tests Title Summarizer (max 3 words + emoji).
2. Tests visual ranking overlay generation (matching @Top6-Ranks style).
3. Tests rendering 3-5 clips with countdown ranks #N to #1.
4. Tests seamless FFmpeg concat demuxer into final vertical short.
"""
import sys
from pathlib import Path

# Force UTF-8 encoding on Windows standard output/error to prevent Unicode encoding crashes
if sys.platform.startswith('win'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import config
from src.logger import logger
from src.narration.title_summarizer import summarize_ranking_title
from src.video.overlay import generate_ranking_compilation_overlay
from src.video.renderer import render_ranking_compilation, _get_audio_duration
from src.reddit.models import RedditPost
from src.reddit.client import download_meme_video


def run_compilation_test():
    logger.info("=== Starting Top 5 Ranking Compilation Test ===")

    # 1. Test Title Summarizer
    test_titles = [
        "Drunk guy tries diving into frozen pool and breaks through ice",
        "Grandfather accidentally drops the wedding cake during speech",
        "Driver loses control on highway barrier after taking sharp turn",
        "Skater tries to jump down 10 stairs and loses his board",
        "Man jumps into deep pool but hits the water slide on the way down"
    ]

    summaries = []
    logger.info("Testing Title Summarizer (max 3 words + emoji):")
    for t in test_titles:
        s = summarize_ranking_title(t)
        summaries.append(s)
        logger.info(f"   Original: '{t[:40]}...' -> Summarized: '{s}'")

    # 2. Test Overlay Generation
    logger.info("Testing Ranking List Overlay Generation:")
    test_rank_titles = {
        1: summaries[0],
        2: summaries[1],
        3: summaries[2],
        4: summaries[3],
        5: summaries[4]
    }

    test_overlay_file = config.OUTPUT_DIR / "test_ranking_overlay_rank_3.png"
    generate_ranking_compilation_overlay(
        active_rank=3,
        total_ranks=5,
        rank_titles=test_rank_titles,
        header_text="Ranking Best Fails",
        filename=test_overlay_file.name
    )
    if test_overlay_file.exists():
        logger.info(f"✔ Overlay successfully generated: {test_overlay_file.name}")
    else:
        logger.error("❌ Failed to generate ranking overlay.")
        sys.exit(1)

    # 3. Test Video Rendering with sample video
    sample_url = "https://github.com/intel-iot-devkit/sample-videos/raw/master/classroom.mp4"
    logger.info(f"Downloading sample MP4 from {sample_url}...")
    sample_path = download_meme_video(sample_url, post_id="test_comp_sample")

    # Create mock clips data (3 clips of 5 seconds each)
    mock_post = RedditPost(
        id="test_mock_1",
        subreddit="Whatcouldgowrong",
        title="Test fail moment",
        selftext="",
        score=2000,
        num_comments=100,
        over_18=False,
        is_self=False,
        permalink="",
        author="tester",
        pinned=False,
        crosspost_parent=None,
        media_url=sample_url
    )

    test_clips_data = [
        {
            "post": mock_post,
            "video_path": sample_path,
            "duration": 5.0,
            "title": summaries[4],
            "rank": 3,
            "score": 1000
        },
        {
            "post": mock_post,
            "video_path": sample_path,
            "duration": 5.0,
            "title": summaries[1],
            "rank": 2,
            "score": 2500
        },
        {
            "post": mock_post,
            "video_path": sample_path,
            "duration": 5.0,
            "title": summaries[0],
            "rank": 1,
            "score": 5000
        }
    ]

    output_test_short = config.OUTPUT_DIR / "test_compilation_final.mp4"
    logger.info(f"Rendering Compilation Short with {len(test_clips_data)} clips...")
    render_ranking_compilation(
        clips_data=test_clips_data,
        output_path=output_test_short,
        header_text="Ranking Best Fails"
    )

    if output_test_short.exists() and output_test_short.stat().st_size > 100000:
        dur = _get_audio_duration(output_test_short)
        size_mb = output_test_short.stat().st_size / (1024 * 1024)
        logger.info(f"🎉 SUCCESS! Compilation rendered successfully:")
        logger.info(f"   Output file: {output_test_short}")
        logger.info(f"   Duration: {dur:.2f}s")
        logger.info(f"   Size: {size_mb:.2f} MB")
        print("\n[SUCCESS] Top 5 Ranking Compilation Integration Test Passed! 🎉")
    else:
        logger.error("❌ Compilation test video was not produced or is empty.")
        sys.exit(1)


if __name__ == "__main__":
    run_compilation_test()
