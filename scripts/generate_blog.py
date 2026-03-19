"""
generate_blog.py
────────────────
Auto AI Blog Generator — SEO/AEO/GEO Optimized
Fetches latest AI news headlines, picks a topic, generates a
600–1000 word blog post following full SEO + human-voice rules,
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
import xml.etree.ElementTree as ET
import requests

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Model fallback chain — tries in order until one succeeds
MODELS = [
    "moonshotai/kimi-k2:free",
    "moonshotai/kimi-k2",
    "mistralai/mistral-7b-instruct:free",
    "meta-llama/llama-3.1-8b-instruct:free",
]

BLOGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "blogs")
MAX_RETRIES = 3
TIMEOUT_SECONDS = 90

# ─────────────────────────────────────────────
# RSS FEEDS — Latest AI News Sources
# ─────────────────────────────────────────────

AI_RSS_FEEDS = [
    "https://techcrunch.com/category/artificial-intelligence/feed/",
    "https://venturebeat.com/category/ai/feed/",
    "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
    "https://feeds.feedburner.com/TheHackersNews",
    "https://www.wired.com/feed/tag/ai/rss",
]

# ─────────────────────────────────────────────
# STATIC AI TOPIC FALLBACK LIST
# Used when all RSS feeds fail
# ─────────────────────────────────────────────

FALLBACK_AI_TOPICS = [
    "GPT-5 vs Claude Opus 4.5: Benchmark Comparison 2026",
    "Google Gemini 2.5 Pro New Features Explained",
    "Meta Llama 4 Open Source Release What You Need to Know",
    "OpenAI o3 Model Real World Performance Review",
    "Anthropic Claude 4 vs GPT-5 Coding Benchmarks",
    "Mistral Large 3 vs Llama 4 Speed and Accuracy Test",
    "AI Agents in 2026 What Actually Works",
    "Best Open Source LLMs for Developers in 2026",
    "Perplexity AI vs ChatGPT Which Search AI Wins",
    "Google Veo 3 vs OpenAI Sora Video Generation Compared",
    "DeepSeek R2 vs OpenAI o3 Reasoning Model Showdown",
    "AI Coding Tools Comparison GitHub Copilot vs Cursor vs Windsurf",
    "Multimodal AI Models GPT-4o vs Gemini Flash vs Claude",
    "Small Language Models That Punch Above Their Weight in 2026",
    "AI Memory and Long Context Windows What the Latest Models Offer",
    "Llama 4 Scout vs Llama 4 Maverick Performance Breakdown",
    "OpenAI GPT-5 Mini Release Date Features and Pricing",
    "AI Image Generation in 2026 Midjourney vs Flux vs Firefly",
    "Reasoning Models Compared o3 vs DeepSeek R2 vs Gemini Thinking",
    "Voice AI Assistants ElevenLabs vs OpenAI Voice vs Google Gemini",
    "AI in Healthcare 2026 Real Deployments and Outcomes",
    "When Will AGI Arrive Researchers Weigh In 2026 Update",
    "Qwen 3 vs DeepSeek V3 Which Chinese AI Leads",
    "Claude 4 Sonnet New Features and Real World Use Cases",
    "AI Startup Funding Report Q1 2026 Who Got What",
]

# ─────────────────────────────────────────────
# BLOG SYSTEM PROMPT — Full SEO/AEO/GEO Rules
# ─────────────────────────────────────────────

SYSTEM_PROMPT = """You are a senior AI tech blogger and SEO strategist. You write blogs that rank on Google, get cited by AI search engines, and sound like a real human wrote them — opinionated, direct, and specific.

WRITING VOICE:
- Write in first person using "I" naturally 3-5 times
- Sound like a knowledgeable friend, not a textbook
- Vary sentence length: mix 5-word punchy lines with 25-word ones
- Include 2+ personal hot takes or opinions
- Include at least 1 contrarian or critical point
- Use casual asides in parentheses occasionally
- Never be generic — every sentence must feel specific

BANNED PHRASES (never use):
- "It's worth noting" / "It's important to note"
- "In today's rapidly evolving landscape"
- "Let's dive in" / "Without further ado"
- "Game-changer" / "Paradigm shift" / "Groundbreaking"
- "In conclusion" / "To sum up"
- "Comprehensive" / "Cutting-edge" / "Leverage" / "Delve"
- "Moreover" / "Furthermore" / "It goes without saying"
- Never start with "In this article we will explore"
- Never use em dash (—). Use commas or periods instead.

BLOG STRUCTURE (follow exactly):
1. H1 Title: Include primary keyword, under 60 chars, compelling hook
2. Opening paragraph: Start with a stat, bold claim, or personal hook. 3-4 sentences.
3. Table of Contents: List all H2 sections with anchor links
4. H2 Sections (4-6 sections): Each section starts with a DIRECT ANSWER in the first sentence. Include specific data, model names, benchmark scores, dates. End each section with your personal take.
5. Comparison Table: Include at least one markdown table comparing models/tools/features
6. FAQ Section: 5-6 questions using exact phrasing people would Google. Answers: 2-3 sentences with specific numbers and names.
7. Closing paragraph: 2-3 sentences. End with a thought-provoking statement or clear recommendation.

SEO RULES:
- Only ONE H1 per post
- H2s should each be answerable standalone queries
- Include specific numbers, dates, model names, benchmark scores throughout
- First sentence of every H2 = direct answer to what the section heading asks

AEO RULES (Answer Engine Optimization):
- FAQ section is MANDATORY — 5-6 questions minimum
- Every section must have at least one quotable single-sentence stat
- Use exact entity names: model versions, company names, benchmark names, scores

GEO RULES (Generative Engine Optimization):
- Every claim needs: WHO, WHAT, WHEN, HOW MUCH
- Include benchmark comparisons with specific numbers
- Add unique analysis or opinions not found elsewhere
- Entity-rich writing: specific model names, scores, release dates, companies

HUMAN VOICE RULES:
- Some sections use bullet points, some don't — vary unpredictably
- Mix short paragraphs (1-2 lines) with longer ones (4-5 lines)
- Add rhetorical questions occasionally
- Never follow the same structure in two consecutive sections

FORMAT:
- Use **bold** for key terms and data points (sparingly)
- Use markdown tables for comparisons
- Keep paragraphs under 4 lines
- Total length: 600-1000 words (body content, not counting headers/metadata)
- Output clean Markdown only"""


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
    """Check OPENROUTER_API_KEY is set. Exit with clear message if not."""
    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        print("=" * 52)
        print("  ERROR: OPENROUTER_API_KEY is not set!")
        print("  Go to: GitHub repo -> Settings -> Secrets")
        print("  -> Actions -> New repository secret")
        print("  Name:  OPENROUTER_API_KEY")
        print("  Value: your sk-or-... key from openrouter.ai")
        print("=" * 52)
        sys.exit(1)
    print(f"[env] OPENROUTER_API_KEY found (length: {len(api_key)} chars).")
    return api_key


# ─────────────────────────────────────────────
# STEP 1: FETCH LATEST AI NEWS FROM RSS
# ─────────────────────────────────────────────

def fetch_ai_headlines_from_rss():
    """
    Pull latest AI news headlines from multiple RSS feeds.
    Filters for AI-related titles.
    Returns a list of headline strings.
    """
    ai_keywords = [
        "ai", "gpt", "llm", "claude", "gemini", "openai", "anthropic",
        "mistral", "llama", "deepseek", "model", "chatgpt", "artificial intelligence",
        "machine learning", "neural", "language model", "generative", "copilot",
        "midjourney", "sora", "perplexity", "qwen", "benchmark", "agent"
    ]

    headlines = []

    for feed_url in AI_RSS_FEEDS:
        try:
            print(f"[rss] Fetching: {feed_url}")
            resp = requests.get(feed_url, timeout=15,
                                headers={"User-Agent": "Mozilla/5.0"})
            if not resp.ok:
                print(f"[rss] Failed {resp.status_code}: {feed_url}")
                continue

            root = ET.fromstring(resp.content)

            # Handle both RSS and Atom feeds
            titles = []
            # RSS format
            for item in root.findall(".//item"):
                title_el = item.find("title")
                if title_el is not None and title_el.text:
                    titles.append(title_el.text.strip())
            # Atom format
            for entry in root.findall(".//{http://www.w3.org/2005/Atom}entry"):
                title_el = entry.find("{http://www.w3.org/2005/Atom}title")
                if title_el is not None and title_el.text:
                    titles.append(title_el.text.strip())

            # Filter for AI-related titles
            for title in titles:
                if any(kw in title.lower() for kw in ai_keywords):
                    headlines.append(title)

            print(f"[rss] Got {len(titles)} titles, {sum(1 for t in titles if any(kw in t.lower() for kw in ai_keywords))} AI-related.")

        except Exception as e:
            print(f"[rss] Error fetching {feed_url}: {e}")
            continue

    # Deduplicate and shuffle
    headlines = list(set(headlines))
    random.shuffle(headlines)
    print(f"[rss] Total unique AI headlines: {len(headlines)}")
    return headlines


def pick_topic(existing_slugs):
    """
    Pick one fresh topic to blog about.
    Priority: RSS live headlines -> static fallback list.
    Skips topics whose slug already exists as a blog file.
    """
    # Try live RSS headlines first
    live_headlines = fetch_ai_headlines_from_rss()

    # Mix live headlines with curated fallback topics for variety
    all_topics = (live_headlines[:15] + FALLBACK_AI_TOPICS) if live_headlines else FALLBACK_AI_TOPICS

    # Filter out already-published slugs
    fresh_topics = [t for t in all_topics if slugify(t) not in existing_slugs]

    if not fresh_topics:
        print("[topic] All known topics used — picking timestamped fallback.")
        ts = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        return f"AI News Roundup {ts}"

    topic = random.choice(fresh_topics[:20])  # pick from top 20 fresh options
    print(f"[topic] Selected: {topic}")
    return topic


# ─────────────────────────────────────────────
# STEP 2: BUILD PROMPT
# ─────────────────────────────────────────────

def build_prompt(topic):
    """Compose the full SEO-optimized blog generation prompt."""
    today = datetime.date.today().strftime("%B %d, %Y")

    return f"""Write a full SEO, AEO, and GEO optimized blog post on this topic.

TOPIC: {topic}
DATE: {today}

REQUIRED OUTPUT FORMAT (produce this exact structure in clean Markdown):

---
**SEO Settings**
- Focus Keyphrase: [primary keyword]
- Title Tag: [under 60 chars]
- Meta Description: [under 155 chars, include a specific stat or name]
- URL Slug: [under 6 words, hyphens, lowercase]
- Tags: [5-6 relevant tags]
---

# [H1 Title — under 60 chars, primary keyword + hook]

[Opening paragraph — start with a stat, bold claim, or personal observation. 3-4 sentences. No "In this article" openings.]

## Table of Contents
- [Section 1 name](#anchor)
- [Section 2 name](#anchor)
- [Section 3 name](#anchor)
- [Section 4 name](#anchor)
- [Section 5 name](#anchor)
- [FAQ](#faq)

---

## [H2 Section 1 — answerable standalone query]
[Direct answer in first sentence. Then 100-150 words with specific data, model names, benchmark scores, dates. End with personal take.]

---

## [H2 Section 2]
[Direct answer in first sentence. Vary format — use a comparison table here if it makes sense.]

---

## [H2 Section 3]
[Direct answer in first sentence. Different format from section 2 — prose paragraphs here.]

---

## [H2 Section 4]
[Direct answer in first sentence. Include your contrarian point or honest criticism here.]

---

## [H2 Section 5 — optional, use if topic warrants it]
[Direct answer. Can be shorter, punchy section.]

---

## FAQ

**[Question 1 — exact phrasing someone would Google]**
[2-3 sentence answer with specific data point]

**[Question 2]**
[2-3 sentence answer]

**[Question 3]**
[2-3 sentence answer]

**[Question 4]**
[2-3 sentence answer]

**[Question 5]**
[2-3 sentence answer]

---

[Closing paragraph — 2-3 sentences. End with a clear recommendation or thought-provoking statement. No "In conclusion".]

---

RULES REMINDER:
- Total word count: 600-1000 words (body only)
- Include at least one comparison table with real model names/scores
- Use "I" naturally 3-5 times
- Include 2+ personal opinions or hot takes
- At least 1 contrarian point
- Never use em dash. No banned phrases.
- Specific numbers, dates, and entity names throughout"""


# ─────────────────────────────────────────────
# STEP 3: CALL OPENROUTER API
# ─────────────────────────────────────────────

def call_openrouter(prompt, api_key):
    """
    Send the prompt to OpenRouter with the system prompt.
    Tries each model in MODELS list until one succeeds.
    Returns raw model output string.
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
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 2000,
            "temperature": 0.75,
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

                if not resp.ok:
                    print(f"[openrouter] Status {resp.status_code}: {resp.text[:500]}")
                    if resp.status_code in (401, 403):
                        print("[openrouter] Auth error. Check your OPENROUTER_API_KEY!")
                        sys.exit(1)
                    resp.raise_for_status()

                data = resp.json()

                if "error" in data:
                    print(f"[openrouter] API error in response: {data['error']}")
                    break  # try next model

                content = data["choices"][0]["message"]["content"].strip()
                word_count = len(content.split())
                print(f"[openrouter] Success with {model}. Word count: ~{word_count}")
                return content

            except requests.exceptions.HTTPError as e:
                print(f"[openrouter] HTTP error on attempt {attempt}: {e}")
            except requests.exceptions.Timeout:
                print(f"[openrouter] Timeout on attempt {attempt}.")
            except Exception as e:
                print(f"[openrouter] Unexpected error on attempt {attempt}: {e}")

            if attempt < MAX_RETRIES:
                print("[openrouter] Retrying in 5 seconds...")
                time.sleep(5)

    raise RuntimeError("All models and retries exhausted. Could not generate blog.")


# ─────────────────────────────────────────────
# STEP 4: PARSE AND EXTRACT METADATA
# ─────────────────────────────────────────────

def extract_seo_settings(raw_text):
    """
    Try to extract SEO settings block from the AI output.
    Returns a dict with title, meta, slug, keyphrase, tags.
    Falls back to reasonable defaults if parsing fails.
    """
    settings = {
        "title_tag": "",
        "meta_description": "",
        "slug": "",
        "keyphrase": "",
        "tags": "",
    }

    patterns = {
        "title_tag":       r"Title Tag[:\s]*(.+)",
        "meta_description": r"Meta Description[:\s]*(.+)",
        "slug":            r"URL Slug[:\s]*(.+)",
        "keyphrase":       r"Focus Keyphrase[:\s]*(.+)",
        "tags":            r"Tags[:\s]*(.+)",
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, raw_text, re.IGNORECASE)
        if match:
            settings[key] = match.group(1).strip().strip("[]").strip()

    return settings


def extract_h1_title(raw_text):
    """Extract the H1 title from markdown output."""
    match = re.search(r"^#\s+(.+)$", raw_text, re.MULTILINE)
    if match:
        return match.group(1).strip()
    # Fallback: first non-empty, non-metadata line
    for line in raw_text.splitlines():
        line = line.strip()
        if line and not line.startswith("---") and not line.startswith("**SEO") and not line.startswith("-"):
            return line.lstrip("#").strip()
    return "AI Blog Post"


def format_final_markdown(raw_content, topic, seo):
    """
    Wrap the AI's blog content in a clean Markdown file with metadata header.
    """
    now_utc = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    today = datetime.date.today().strftime("%B %d, %Y")

    meta_block = (
        f"<!--\n"
        f"  Auto-generated blog post\n"
        f"  Generated: {now_utc}\n"
        f"  Topic: {topic}\n"
        f"  Focus Keyphrase: {seo.get('keyphrase', '')}\n"
        f"  Title Tag: {seo.get('title_tag', '')}\n"
        f"  Meta Description: {seo.get('meta_description', '')}\n"
        f"  Tags: {seo.get('tags', '')}\n"
        f"-->\n\n"
    )

    footer = (
        f"\n\n---\n\n"
        f"*Published: {today} | "
        f"Auto-generated by [Auto AI Blog Generator](https://github.com/auto-ai-blog-generator)*\n"
    )

    # Strip the SEO settings block from visible content (it's in HTML comment above)
    cleaned = re.sub(
        r"---\s*\*\*SEO Settings\*\*.*?---",
        "",
        raw_content,
        flags=re.DOTALL
    ).strip()

    return meta_block + cleaned + footer


# ─────────────────────────────────────────────
# STEP 5: SAVE FILE
# ─────────────────────────────────────────────

def save_blog(title, content, seo_slug=""):
    """
    Save the Markdown blog to /blogs/<slug>.md.
    Prefers the AI-generated SEO slug; falls back to slugified title.
    Returns the saved file path, or raises FileExistsError.
    """
    blogs_path = os.path.abspath(BLOGS_DIR)
    os.makedirs(blogs_path, exist_ok=True)

    # Prefer AI-generated slug; fallback to title slug
    slug = slugify(seo_slug) if seo_slug else ""
    if not slug:
        slug = slugify(title)
    if not slug:
        slug = f"blog-{datetime.datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"

    # Trim slug to reasonable length (max 60 chars)
    slug = slug[:60].rstrip("-")

    filename = f"{slug}.md"
    filepath = os.path.join(blogs_path, filename)

    if os.path.exists(filepath):
        raise FileExistsError(f"Blog already exists: {filename}")

    with open(filepath, "w", encoding="utf-8") as fh:
        fh.write(content)

    print(f"[save] Blog saved -> blogs/{filename}")
    return filepath


# ─────────────────────────────────────────────
# STEP 6: GET EXISTING SLUGS
# ─────────────────────────────────────────────

def get_existing_slugs():
    """Return set of slugs for all existing blog files."""
    existing = set()
    blogs_path = os.path.abspath(BLOGS_DIR)
    if os.path.isdir(blogs_path):
        for fname in os.listdir(blogs_path):
            if fname.endswith(".md"):
                existing.add(fname[:-3])
    print(f"[slugs] Found {len(existing)} existing blog files.")
    return existing


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    print("=" * 52)
    print("  Auto AI Blog Generator — Starting Run")
    print("=" * 52)

    # 0. Validate environment
    api_key = validate_env()

    # 1. Get existing slugs for duplicate check
    existing_slugs = get_existing_slugs()

    # 2. Pick a fresh AI topic (RSS first, then fallback)
    topic = pick_topic(existing_slugs)

    # 3. Build prompt and call AI
    prompt = build_prompt(topic)
    raw_text = call_openrouter(prompt, api_key)

    if not raw_text or len(raw_text.split()) < 100:
        print(f"[error] AI returned too little content ({len(raw_text.split())} words). Aborting.")
        print("NEW_BLOG_CREATED=false")
        sys.exit(0)

    # 4. Extract SEO settings and title from AI output
    seo = extract_seo_settings(raw_text)
    h1_title = extract_h1_title(raw_text)
    print(f"[parse] H1 title: {h1_title}")
    print(f"[parse] SEO slug: {seo.get('slug', '(none)')}")
    print(f"[parse] Keyphrase: {seo.get('keyphrase', '(none)')}")

    # 5. Format final Markdown
    final_content = format_final_markdown(raw_text, topic, seo)

    # 6. Save file
    try:
        filepath = save_blog(h1_title, final_content, seo_slug=seo.get("slug", ""))
        print(f"[done] New blog created: {filepath}")
        print("NEW_BLOG_CREATED=true")
    except FileExistsError as e:
        print(f"[skip] {e} -- nothing to commit.")
        print("NEW_BLOG_CREATED=false")
        sys.exit(0)

    print("=" * 52)
    print("  Run Complete!")
    print("=" * 52)


if __name__ == "__main__":
    main()
