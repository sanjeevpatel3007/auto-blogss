"""
generate_blog.py
────────────────
Auto AI Blog Generator — Main Script
Fetches a trending topic, generates a short blog post via OpenRouter,
and saves it as a Markdown file inside /blogs/.

Environment variables required:
  OPENROUTER_API_KEY  – your OpenRouter API key
"""

import os
import re
import sys
import random
import datetime
import requests

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "moonshotai/kimi-k2:free"  # kimi-k2.5 via OpenRouter
BLOGS_DIR = os.path.join(os.path.dirname(__file__), "..", "blogs")
MAX_RETRIES = 3
TIMEOUT_SECONDS = 60

# ─────────────────────────────────────────────
# STATIC FALLBACK TOPICS
# Used when pytrends or any live feed fails.
# Freely add or remove topics here.
# ─────────────────────────────────────────────

FALLBACK_TOPICS = [
    "Artificial Intelligence in Healthcare",
    "Quantum Computing Breakthroughs",
    "Electric Vehicles Future",
    "Generative AI for Developers",
    "Climate Tech Innovations",
    "GPT Models and Their Impact",
    "Cybersecurity in 2025",
    "Space Exploration Updates",
    "Robotics and Automation",
    "Blockchain Beyond Crypto",
    "Open Source AI Models",
    "Edge Computing Trends",
    "Smart Cities and IoT",
    "AI Chip Breakthroughs",
    "Wearable Tech Evolution",
    "Neural Interfaces Development",
    "Renewable Energy Storage",
    "Autonomous Vehicles Update",
    "Augmented Reality in Business",
    "AI Regulation and Ethics",
    "5G and 6G Technology",
    "Digital Health Platforms",
    "AI-Powered Code Editors",
    "Data Privacy Laws 2025",
    "Humanoid Robots Progress",
    "Large Language Model Advances",
    "Satellite Internet Expansion",
    "Biometric Security Technology",
    "AI in Education",
    "Sustainable Technology Trends",
]


# ─────────────────────────────────────────────
# HELPER: SLUGIFY
# ─────────────────────────────────────────────


def slugify(text: str) -> str:
    """Convert a title string to a URL-friendly filename slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)  # remove special chars
    text = re.sub(r"[\s_]+", "-", text)  # spaces/underscores → hyphens
    text = re.sub(r"-+", "-", text)  # collapse multiple hyphens
    return text.strip("-")


# ─────────────────────────────────────────────
# STEP 1: GET TRENDING TOPIC
# ─────────────────────────────────────────────


def get_trending_topics_pytrends() -> list:
    """
    Attempt to fetch today's trending Google searches (US).
    Returns a list of strings, or [] on any failure.
    """
    try:
        from pytrends.request import TrendReq

        pytrends = TrendReq(hl="en-US", tz=360, timeout=(10, 30))
        trending_df = pytrends.trending_searches(pn="united_states")
        topics = trending_df[0].tolist()
        print(f"[pytrends] Fetched {len(topics)} trending topics.")
        return topics
    except Exception as e:
        print(f"[pytrends] Could not fetch live trends: {e}")
        return []


def pick_topic() -> str:
    """
    Pick one fresh topic to blog about.
    Priority order: pytrends live data → static fallback list.
    Skips topics whose slug already exists as a blog file.
    """
    live_topics = get_trending_topics_pytrends()
    all_topics = live_topics if live_topics else FALLBACK_TOPICS

    # Collect slugs of already-published blogs
    existing_slugs = set()
    blogs_path = os.path.abspath(BLOGS_DIR)
    if os.path.isdir(blogs_path):
        for fname in os.listdir(blogs_path):
            if fname.endswith(".md"):
                existing_slugs.add(fname[:-3])  # strip .md

    # Keep only topics not yet published
    fresh_topics = [t for t in all_topics if slugify(t) not in existing_slugs]

    if not fresh_topics:
        # All known topics covered — just pick a random fallback anyway
        print("[topic] All topics already used — picking random fallback.")
        return random.choice(FALLBACK_TOPICS)

    topic = random.choice(fresh_topics)
    print(f"[topic] Selected: {topic}")
    return topic


# ─────────────────────────────────────────────
# STEP 2: GENERATE BLOG VIA OPENROUTER
# ─────────────────────────────────────────────


def build_prompt(topic: str) -> str:
    """Compose the AI prompt for a short, engaging blog post."""
    today = datetime.date.today().strftime("%B %d, %Y")
    return (
        f"You are a tech blogger. Write a very short, engaging blog post about the topic below.\n\n"
        f"Topic: {topic}\n"
        f"Date: {today}\n\n"
        f"Requirements:\n"
        f"- First line: a catchy blog TITLE (plain text only, no # symbol)\n"
        f"- Then a blank line\n"
        f"- Then the blog body: 100–200 words\n"
        f"- Simple English, informative, feels like fresh news\n"
        f"- No headers or bullet points in the body — just flowing paragraphs\n"
        f"- End with one punchy closing sentence\n\n"
        f"Output ONLY the title and blog body. Nothing else."
    )


def call_openrouter(prompt: str) -> str:
    """
    Send the prompt to OpenRouter and return the raw model output.
    Retries up to MAX_RETRIES times on transient failures.
    """
    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise EnvironmentError("OPENROUTER_API_KEY environment variable is not set.")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/auto-ai-blog-generator",
        "X-Title": "Auto AI Blog Generator",
    }

    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 400,
        "temperature": 0.8,
    }

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"[openrouter] Attempt {attempt}/{MAX_RETRIES} ...")
            resp = requests.post(
                OPENROUTER_API_URL,
                headers=headers,
                json=payload,
                timeout=TIMEOUT_SECONDS,
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"].strip()
            print("[openrouter] Generation successful.")
            return content
        except requests.exceptions.HTTPError as e:
            last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
            print(f"[openrouter] HTTP error: {last_error}")
        except requests.exceptions.Timeout:
            last_error = "Request timed out."
            print(f"[openrouter] {last_error}")
        except Exception as e:
            last_error = str(e)
            print(f"[openrouter] Unexpected error: {last_error}")

        if attempt < MAX_RETRIES:
            print("[openrouter] Retrying in 3 seconds...")
            import time

            time.sleep(3)

    raise RuntimeError(
        f"OpenRouter API failed after {MAX_RETRIES} attempts. Last error: {last_error}"
    )


# ─────────────────────────────────────────────
# STEP 3: PARSE AI OUTPUT
# ─────────────────────────────────────────────


def parse_blog(raw_text: str) -> tuple[str, str]:
    """
    Split AI output into (title, body).
    First non-empty line → title (strips any leading # characters).
    Remaining lines → body.
    """
    lines = [line.strip() for line in raw_text.strip().splitlines() if line.strip()]

    if not lines:
        return "Untitled Blog", ""

    # Clean up any markdown heading symbols the model might have added
    title = lines[0].lstrip("#").strip()

    # Everything after the first line is the body
    body = "\n\n".join(lines[1:]) if len(lines) > 1 else ""

    return title, body


def format_markdown(title: str, body: str, topic: str) -> str:
    """Wrap title + body into a well-formatted Markdown document."""
    now_utc = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    return (
        f"# {title}\n\n"
        f"> *Generated on {now_utc} | Topic: {topic}*\n\n"
        f"---\n\n"
        f"{body}\n\n"
        f"---\n\n"
        f"*This blog was auto-generated by "
        f"[Auto AI Blog Generator](https://github.com/auto-ai-blog-generator).*\n"
    )


# ─────────────────────────────────────────────
# STEP 4: SAVE FILE
# ─────────────────────────────────────────────


def save_blog(title: str, content: str) -> str:
    """
    Save the formatted Markdown to /blogs/<slug>.md.
    Returns the saved file path.
    Raises FileExistsError if a file with that slug already exists.
    """
    os.makedirs(os.path.abspath(BLOGS_DIR), exist_ok=True)

    slug = slugify(title)
    filename = f"{slug}.md"
    filepath = os.path.join(os.path.abspath(BLOGS_DIR), filename)

    if os.path.exists(filepath):
        raise FileExistsError(f"Blog already exists: {filename}")

    with open(filepath, "w", encoding="utf-8") as fh:
        fh.write(content)

    print(f"[save] Blog saved → blogs/{filename}")
    return filepath


# ─────────────────────────────────────────────
# MAIN ENTRY POINT
# ─────────────────────────────────────────────


def main():
    print("=" * 52)
    print("  Auto AI Blog Generator — Starting Run")
    print("=" * 52)

    # 1. Pick a fresh topic
    topic = pick_topic()

    # 2. Build prompt and call AI model
    prompt = build_prompt(topic)
    raw_text = call_openrouter(prompt)

    # 3. Parse the AI response
    title, body = parse_blog(raw_text)
    print(f"[parse] Blog title: {title}")

    # 4. Build final Markdown content
    markdown_content = format_markdown(title, body, topic)

    # 5. Save to /blogs/
    try:
        filepath = save_blog(title, markdown_content)
        print(f"[done] New blog created: {filepath}")
        # Used by the GitHub Actions step to decide whether to commit
        print("NEW_BLOG_CREATED=true")
    except FileExistsError as e:
        print(f"[skip] {e} — nothing to commit.")
        print("NEW_BLOG_CREATED=false")
        sys.exit(0)

    print("=" * 52)
    print("  Run Complete!")
    print("=" * 52)


if __name__ == "__main__":
    main()
