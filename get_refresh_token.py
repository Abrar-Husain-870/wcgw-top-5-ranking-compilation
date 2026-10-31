#!/usr/bin/env python3
"""
Helper script: Generate a YouTube OAuth refresh token for a new channel.

Usage:
    python get_refresh_token.py

Then paste the printed REFRESH_TOKEN into your .env file.
Uses the same YT_CLIENT_ID and YT_CLIENT_SECRET_VALUE from your .env.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Force UTF-8 encoding on Windows standard output/error to prevent Unicode encoding crashes
if sys.platform.startswith('win'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True, write_through=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True, write_through=True)

ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(ENV_PATH, override=True)

import config

# Re-read in case imported before override
YT_CLIENT_ID = os.environ.get("YT_CLIENT_ID") or config.YT_CLIENT_ID
YT_CLIENT_SECRET = os.environ.get("YT_CLIENT_SECRET_VALUE") or config.YT_CLIENT_SECRET


def main() -> None:
    global YT_CLIENT_ID, YT_CLIENT_SECRET
    
    if not YT_CLIENT_ID or "your_client_id" in YT_CLIENT_ID:
        print("=" * 60)
        print("🔑 YOUTUBE CLIENT ID & SECRET SETUP")
        print("=" * 60)
        print("Please paste your Client ID from Google Cloud Console:")
        try:
            YT_CLIENT_ID = input("YT_CLIENT_ID: ").strip().strip('"').strip("'")
        except (KeyboardInterrupt, EOFError):
            sys.exit(1)

    if not YT_CLIENT_SECRET:
        print("Please paste your Client Secret from Google Cloud Console:")
        try:
            YT_CLIENT_SECRET = input("YT_CLIENT_SECRET_VALUE: ").strip().strip('"').strip("'")
        except (KeyboardInterrupt, EOFError):
            sys.exit(1)

    if not YT_CLIENT_ID or not YT_CLIENT_SECRET:
        print("❌ Client ID and Client Secret are required!")
        sys.exit(1)

    # Automatically save them into .env so the user never has to do it manually
    if ENV_PATH.exists():
        try:
            import re
            content = ENV_PATH.read_text(encoding="utf-8")
            if "YT_CLIENT_ID=" in content:
                content = re.sub(r'YT_CLIENT_ID=.*', f'YT_CLIENT_ID={YT_CLIENT_ID}', content)
            else:
                content += f"\nYT_CLIENT_ID={YT_CLIENT_ID}"
                
            if "YT_CLIENT_SECRET_VALUE=" in content:
                content = re.sub(r'YT_CLIENT_SECRET_VALUE=.*', f'YT_CLIENT_SECRET_VALUE={YT_CLIENT_SECRET}', content)
            else:
                content += f"\nYT_CLIENT_SECRET_VALUE={YT_CLIENT_SECRET}"
                
            ENV_PATH.write_text(content, encoding="utf-8")
            print(f"✔ Saved YT_CLIENT_ID and YT_CLIENT_SECRET_VALUE into {ENV_PATH.name}")
        except Exception as e:
            print(f"⚠️ Could not auto-save to .env: {e}")

    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.oauth2.credentials import Credentials

    SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

    client_config = {
        "installed": {
            "client_id": YT_CLIENT_ID,
            "client_secret": YT_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }

    print("=" * 60)
    print("🔑 YOUTUBE REFRESH TOKEN GENERATOR")
    print("=" * 60)
    print()
    print("⚠️  IMPORTANT: When the browser opens, sign in with your")
    print("   NEW channel's email address (not your old one)!")
    print()
    print("   Then click 'Continue' to grant access.")
    print()

    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    creds = flow.run_local_server(port=0, open_browser=True)

    new_token = creds.refresh_token

    print()
    print("=" * 60)
    print("✅ SUCCESS! Here is your new refresh token:")
    print()
    print(f"   {new_token}")
    print()
    print("=" * 60)
    print()

    # Automatically update local .env file
    env_path = config.ROOT / ".env"
    if env_path.exists():
        try:
            content = env_path.read_text(encoding="utf-8")
            lines = content.splitlines()
            new_lines = []
            updated_ref = False
            updated_meme_ref = False
            for line in lines:
                if line.startswith("YT_REFRESH_TOKEN="):
                    new_lines.append(f'YT_REFRESH_TOKEN="{new_token}"')
                    updated_ref = True
                elif line.startswith("YT_MEME_REFRESH_TOKEN="):
                    new_lines.append(f'YT_MEME_REFRESH_TOKEN="{new_token}"')
                    updated_meme_ref = True
                else:
                    new_lines.append(line)
            if not updated_ref:
                new_lines.append(f'YT_REFRESH_TOKEN="{new_token}"')
            if not updated_meme_ref:
                new_lines.append(f'YT_MEME_REFRESH_TOKEN="{new_token}"')
            env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
            print("✔ Automatically updated local .env file with new refresh token!")
        except Exception as e:
            print(f"⚠️ Could not auto-update .env file: {e}")

    # Invalidate old cached token so new account is immediately active
    token_file = config.CACHE_DIR / "yt_token.json"
    if token_file.exists():
        try:
            token_file.unlink()
            print("✔ Cleared previous cached YouTube session token.")
        except Exception as e:
            print(f"⚠️ Could not delete old cached token: {e}")

    print()
    print("📌 IMPORTANT: If using GitHub Actions, update GitHub Secrets:")
    print(f'   YT_REFRESH_TOKEN = {new_token}')
    print(f'   YT_MEME_REFRESH_TOKEN = {new_token}')
    print()


if __name__ == "__main__":
    main()