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
import time
import requests

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Model options — script tries each in order until one succeeds
MODELS = [
    "moonshotai/kimi-k2:free",
    "moonshotai/kimi-k2",
    "mistralai/mistral-7b-instruct:free",
    "meta-llama/llama-3.1-8b-instruct:free",
]

BLOGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "blogs")
MAX_RETRIES = 3
TIMEOUT_SECONDS = 60

# ─────────────────────────────────────────────
# STATIC FALLBACK TOPICS
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

def slugify(text):
    """Convert a title string to a URL-friendly filename slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


# ─────────────────────────────────────────────
# STEP 0: VALIDATE ENVIRONMENT
# ─────────────────────────────────────────────

def validate_env():
    """
    Check required environment variables before doing anything else.
    Exits with a clear message if something is missing.
    """
    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        print("=" * 52)
        print("  ERROR: OPENROUTER_API_KEY is not set!")
        print("  Go to: GitHub repo → Settings → Secrets")
        print("  → Actions → New repository secret")
        print("  Name:  OPENROUTER_API_KEY")
        print("  Value: your sk-or-... key from openrouter.ai")
        print("=" * 52)
        sys.exit(1)
    print(f"[env] OPENROUTER_API_KEY found (length: {len(api_key)} chars).")
    return api_key


# ─────────────────────────────────────────────
# STEP 1: GET TRENDING TOPIC
# ─────────────────────────────────────────────

def get_trending_topics_pytrends():
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


def pick_topic():
    """
    Pick one fresh topic to blog about.
    Priority: pytrends live data → static fallback list.
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
                existing_slugs.add(fname[:-3])

    # Keep only topics not yet published
    fresh_topics = [t for t in all_topics if slugify(t) not in existing_slugs]

    if not fresh_topics:
        print("[topic] All topics already used — picking random fallback.")
        return random.choice(FALLBACK_TOPICS)

    topic = random.choice(fresh_topics)
    print(f"[topic] Selected: {topic}")
    return topic


# ─────────────────────────────────────────────
# STEP 2: GENERATE BLOG VIA OPENROUTER
# ─────────────────────────────────────────────

def build_prompt(topic):
    """Compose the AI prompt for a short, engaging blog post."""
    today = datetime.date.today().strftime("%B %d, %Y")
    return (
        "You are a tech blogger. Write a very short, engaging blog post.\n\n"
        f"Topic: {topic}\n"
        f"Date: {today}\n\n"
        "Rules:\n"
        "- Line 1: blog TITLE only (plain text, no # symbol, no quotes)\n"
        "- Line 2: blank\n"
        "- Lines 3+: blog body, 100-200 words, simple English\n"
        "- No bullet points or sub-headers in the body\n"
        "- End with one punchy closing sentence\n\n"
        "Output ONLY the title and body. Nothing else."
    )


def call_openrouter(prompt, api_key):
    """
    Send the prompt to OpenRouter, trying each model in MODELS list.
    Returns the raw model output string.
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/auto-ai-blog-generator",
        "X-Title": "Auto AI Blog Generator",
    }

    for model in MODELS:
        print(f"[openrouter] Trying model: {model}")
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 500,
            "temperature": 0.8,
        }

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                print(f"[openrouter] Attempt {attempt}/{MAX_RETRIES} ...")
                resp = requests.post(
                    OPENROUTER_API_URL,
                    headers=headers,
                    json=payload,
                    timeout=TIMEOUT_SECONDS,
                )

                # Log full error response for debugging
                if not resp.ok:
                    print(f"[openrouter] Status {resp.status_code}: {resp.text[:500]}")
                    resp.raise_for_status()

                data = resp.json()

                # Check for API-level errors inside a 200 response
                if "error" in data:
                    print(f"[openrouter] API error in response: {data['error']}")
                    break  # try next model

                content = data["choices"][0]["message"]["content"].strip()
                print(f"[openrouter] Success with model: {model}")
                return content

            except requests.exceptions.HTTPError as e:
                print(f"[openrouter] HTTP error on attempt {attempt}: {e}")
                if resp.status_code in (401, 403):
                    print("[openrouter] Auth error — check your OPENROUTER_API_KEY!")
                    sys.exit(1)  # no point retrying auth errors
            except requests.exceptions.Timeout:
                print(f"[openrouter] Timeout on attempt {attempt}.")
            except Exception as e:
                print(f"[openrouter] Unexpected error on attempt {attempt}: {e}")

            if attempt < MAX_RETRIES:
                print("[openrouter] Retrying in 5 seconds...")
                time.sleep(5)

    raise RuntimeError("All models and retries exhausted. Could not generate blog.")


# ─────────────────────────────────────────────
# STEP 3: PARSE AI OUTPUT
# ─────────────────────────────────────────────

def parse_blog(raw_text):
    """
    Split AI output into (title, body).
    First non-empty line → title.
    Remaining non-empty lines → body.
    """
    lines = raw_text.strip().splitlines()
    non_empty = [l.strip() for l in lines if l.strip()]

    if not non_empty:
        return "Untitled Blog", "No content generated."

    # Strip any markdown heading symbols the model might add
    title = non_empty[0].lstrip("#").strip().strip('"').strip("'")

    body = "\n\n".join(non_empty[1:]) if len(non_empty) > 1 else ""

    return title, body


def format_markdown(title, body, topic):
    """Wrap title + body into a formatted Markdown document."""
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

def save_blog(title, content):
    """
    Save the formatted Markdown to /blogs/<slug>.md.
    Returns the saved file path, or raises FileExistsError.
    """
    blogs_path = os.path.abspath(BLOGS_DIR)
    os.makedirs(blogs_path, exist_ok=True)

    slug = slugify(title)
    if not slug:
        # Fallback slug using timestamp if title produces empty slug
        slug = f"blog-{datetime.datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"

    filename = f"{slug}.md"
    filepath = os.path.join(blogs_path, filename)

    if os.path.exists(filepath):
        raise FileExistsError(f"Blog already exists: {filename}")

    with open(filepath, "w", encoding="utf-8") as fh:
        fh.write(content)

    print(f"[save] Blog saved → blogs/{filename}")
    return filepath


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    print("=" * 52)
    print("  Auto AI Blog Generator — Starting Run")
    print("=" * 52)

    # 0. Validate environment first (fast-fail with clear message)
    api_key = validate_env()

    # 1. Pick a fresh topic
    topic = pick_topic()

    # 2. Build prompt and call AI
    prompt = build_prompt(topic)
    raw_text = call_openrouter(prompt, api_key)

    # 3. Parse the AI response
    title, body = parse_blog(raw_text)
    print(f"[parse] Blog title: {title}")

    if not body:
        print("[error] AI returned empty body — skipping.")
        print("NEW_BLOG_CREATED=false")
        sys.exit(0)

    # 4. Format as Markdown
    markdown_content = format_markdown(title, body, topic)

    # 5. Save to /blogs/
    try:
        filepath = save_blog(title, markdown_content)
        print(f"[done] New blog created: {filepath}")
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
