"""
RAJ ASSISTANT - AI-Powered Facebook Messenger Bot
Trained to sound exactly like Mo The Jeweler

Handles Facebook webhook verification and incoming messages,
responds with Claude using Mo's complete personality profile.
"""

import os
import json
import logging
import asyncio
import tempfile
import random
import re
import time
import xml.etree.ElementTree as ET
from typing import Set
from fastapi import FastAPI, Request, HTTPException, Response
from anthropic import Anthropic
import requests
from dotenv import load_dotenv
from anthropic_utils import create_message_with_model_fallback, get_anthropic_model

# Load environment variables from .env
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="Raj Assistant - Mo The Jeweler Bot")

# Initialize Anthropic client
client = Anthropic()

# Get credentials from environment
FACEBOOK_PAGE_ACCESS_TOKEN = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN", "")
FACEBOOK_WEBHOOK_VERIFY_TOKEN = os.getenv("FACEBOOK_WEBHOOK_VERIFY_TOKEN", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import personality system prompt
try:
    from personality import get_raj_complete_system_prompt
    RAJ_SYSTEM_PROMPT = get_raj_complete_system_prompt()
except ImportError:
    logger.warning("Could not import personality module, using fallback system prompt")
    RAJ_SYSTEM_PROMPT = "You are Raj, an AI assistant trained to sound like Mo The Jeweler, owner of Saif Jewelers in Texas. Be authentic, transparent, and helpful when discussing jewelry, pricing, and custom services."

try:
    from video_personality_updater import PersonalityVideoUpdater
except ImportError:
    PersonalityVideoUpdater = None

try:
    from voice_synth import VoiceSynthesizer
except ImportError:
    VoiceSynthesizer = None

try:
    from runtime_editor import RuntimeEditor
except ImportError:
    RuntimeEditor = None

YOUTUBE_CHANNEL_ID = os.getenv("YOUTUBE_CHANNEL_ID", "")
YOUTUBE_CHANNEL_RSS_URL = os.getenv("YOUTUBE_CHANNEL_RSS_URL", "")
PERSONALITY_REFRESH_MINUTES = int(os.getenv("PERSONALITY_REFRESH_MINUTES", "60"))
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "")
VOICE_PROVIDER = os.getenv("VOICE_PROVIDER", "none")
OWNER_FACEBOOK_IDS_RAW = os.getenv("OWNER_FACEBOOK_IDS", "")

OWNER_FACEBOOK_IDS: Set[str] = {
    x.strip() for x in OWNER_FACEBOOK_IDS_RAW.split(",") if x.strip()
}
ANTHROPIC_MODEL = get_anthropic_model()
WEBSITE_BASE_URL = os.getenv("WEBSITE_BASE_URL", "")
WEBSITE_SITEMAP_URL = os.getenv("WEBSITE_SITEMAP_URL", "")
WEBSITE_INVENTORY_URL = os.getenv("WEBSITE_INVENTORY_URL", WEBSITE_BASE_URL)
MOLD_KIT_URL = os.getenv("MOLD_KIT_URL", WEBSITE_BASE_URL)
IN_PERSON_URL = os.getenv("IN_PERSON_URL", WEBSITE_BASE_URL)
GRILLZ_PRICING_URL = os.getenv("GRILLZ_PRICING_URL", "our website")
RESPONSE_DELAY_MIN_SECONDS = int(os.getenv("DM_RESPONSE_DELAY_MIN_SECONDS", "60"))
RESPONSE_DELAY_MAX_SECONDS = int(os.getenv("DM_RESPONSE_DELAY_MAX_SECONDS", "180"))
DM_BURST_WINDOW_SECONDS = int(os.getenv("DM_BURST_WINDOW_SECONDS", "120"))
DM_BURST_THRESHOLD = int(os.getenv("DM_BURST_THRESHOLD", "2"))
WEBSITE_LINK_CACHE_TTL_SECONDS = int(os.getenv("WEBSITE_LINK_CACHE_TTL_SECONDS", "900"))
SYNC_LOCK_PATH = os.getenv(
    "RAJ_SYNC_LOCK_PATH",
    os.path.join(tempfile.gettempdir(), "raj_personality_sync.lock"),
)

video_updater = None
if PersonalityVideoUpdater is not None:
    video_updater = PersonalityVideoUpdater(
        channel_id=YOUTUBE_CHANNEL_ID,
        rss_url=YOUTUBE_CHANNEL_RSS_URL,
    )

sync_task = None
sync_lock_fd = None
recent_inbound_by_sender = {}
pending_response_tasks = {}
website_link_cache = {"fetched_at": 0.0, "links": []}

voice_synth = VoiceSynthesizer(provider=VOICE_PROVIDER) if VoiceSynthesizer else None
runtime_editor = RuntimeEditor(default_refresh_minutes=PERSONALITY_REFRESH_MINUTES) if RuntimeEditor else None


def is_owner_sender(sender_id: str) -> bool:
    if not sender_id:
        return False
    return sender_id in OWNER_FACEBOOK_IDS


def sanitize_dm_response(text: str) -> str:
    """Keep responses short/simple and remove self-identifying intros."""
    cleaned = (text or "").strip()
    if not cleaned:
        return "What's up? What can I help you with?"

    intro_pattern = re.compile(
        r"^(?:hey\s*,?\s*)?(?:yo\s*,?\s*)?"
        r"(?:this is|i am|i'm|im|it'?s)?\s*"
        r"(?:raj|mo(?:e)?)(?:\s+the\s+jeweler)?\s*[,\-:]?\s*",
        re.IGNORECASE,
    )
    cleaned = re.sub(intro_pattern, "", cleaned).strip()

    # Remove identity mentions if they appear later in the response too.
    cleaned = re.sub(
        r"\b(?:this is|i am|i'm|im|it'?s)\s+(?:raj|mo(?:e)?)(?:\s+the\s+jeweler)?\b[\s,.:;!-]*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    ).strip()
    cleaned = re.sub(
        r"\b(?:raj|mo(?:e)?)\s+here\b[\s,.:;!-]*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    ).strip()

    # Keep conversation moving with concise 1-2 sentence replies.
    parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", cleaned) if p.strip()]
    if parts:
        cleaned = parts[0]

    if len(cleaned) > 160:
        cleaned = cleaned[:160].rsplit(" ", 1)[0].rstrip(" ,;:-") + "..."

    return cleaned or "What's up? What can I help you with?"


def is_greeting_only_message(message_text: str) -> bool:
    text = (message_text or "").strip().lower()
    if not text:
        return True

    normalized = re.sub(r"[^a-z0-9\s]", "", text)
    greeting_phrases = {
        "hi", "hey", "hello", "yo", "sup", "whats up", "what up",
        "good morning", "good afternoon", "good evening", "hows it going",
        "hola", "buenas", "que tal", "q tal", "todo bien", "como va",
        "buen dia", "buenas tardes", "buenas noches",
    }
    return normalized in greeting_phrases


def pick_short_context_sentence(user_message: str, model_text: str) -> str:
    """Pick a short sentence that answers context, not just repeated greeting."""
    parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", (model_text or "").strip()) if p.strip()]
    if not parts:
        return sanitize_dm_response(model_text)

    if is_greeting_only_message(user_message):
        return sanitize_dm_response(parts[0])

    # If user asked a real question, skip pure greeting lead-ins when possible.
    first_is_greeting = bool(re.match(r"^(yo|hey|hi|hello|what'?s up)\b", parts[0], re.IGNORECASE))
    if first_is_greeting and len(parts) > 1:
        return sanitize_dm_response(parts[1])

    return sanitize_dm_response(parts[0])


def build_first_intro(user_message: str) -> str:
    """Only for the first message in a thread."""
    msg = (user_message or "").lower()
    if any(x in msg for x in ["hola", "buenas", "que tal", "q tal"]):
        return "Que tal, en que te ayudo?"
    return "What's up, what can I help you with?"


def parse_xml_links(xml_text: str) -> list[str]:
    """Extract URL links from sitemap XML."""
    links = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return links

    for element in root.iter():
        if element.tag.endswith("loc") and element.text:
            url = element.text.strip()
            if url:
                links.append(url)
    return links


def fetch_website_links() -> list[str]:
    """Fetch and cache website links from sitemap for product link matching."""
    now = time.time()
    cached_links = website_link_cache.get("links", [])
    fetched_at = float(website_link_cache.get("fetched_at", 0.0))

    if cached_links and (now - fetched_at) < max(60, WEBSITE_LINK_CACHE_TTL_SECONDS):
        return cached_links

    if not WEBSITE_SITEMAP_URL:
        website_link_cache["fetched_at"] = now
        website_link_cache["links"] = []
        return []

    try:
        response = requests.get(WEBSITE_SITEMAP_URL, timeout=12)
        response.raise_for_status()
        links = parse_xml_links(response.text)
        website_link_cache["fetched_at"] = now
        website_link_cache["links"] = links
        return links
    except Exception as exc:
        logger.warning("Unable to fetch sitemap links: %s", exc)
        website_link_cache["fetched_at"] = now
        return cached_links


def match_inventory_links(message_text: str, max_links: int = 2) -> list[str]:
    """Find best matching product/inventory links from sitemap."""
    msg = (message_text or "").lower()
    links = fetch_website_links()
    if not links:
        return [WEBSITE_INVENTORY_URL] if WEBSITE_INVENTORY_URL else []

    non_product_markers = [
        "about", "contact", "faq", "blog", "privacy", "policy", "terms", "shipping",
        "returns", "refund", "login", "account", "cart", "checkout", "search", "track-order",
    ]
    product_markers = [
        "product", "products", "shop", "collection", "collections", "inventory",
        "grill", "ring", "chain", "bracelet", "pendant", "necklace", "earring", "watch",
    ]

    # Keep only product/collection pages and explicitly remove non-product pages.
    inventory_links = []
    for url in links:
        lower = url.lower()
        if any(x in lower for x in non_product_markers):
            continue
        if any(x in lower for x in product_markers):
            inventory_links.append(url)

    if not inventory_links:
        inventory_links = links

    # If this is a chain request, prioritize chain-related URLs only.
    if is_chain_intent(msg):
        chain_links = [
            url for url in inventory_links
            if any(x in url.lower() for x in ["chain", "chains", "cadena", "necklace", "cuban", "rope", "figaro", "franco", "tennis"])
        ]
        if chain_links:
            inventory_links = chain_links

    terms = [t for t in re.split(r"[^a-z0-9]+", msg) if len(t) >= 3]
    if not terms:
        return [WEBSITE_INVENTORY_URL] if WEBSITE_INVENTORY_URL else []

    scored = []
    for url in inventory_links:
        path = url.lower()
        score = sum(1 for t in terms if t in path)
        if score > 0:
            scored.append((score, url))

    scored.sort(key=lambda x: x[0], reverse=True)
    out = [url for _, url in scored[:max_links]]
    if not out and WEBSITE_INVENTORY_URL:
        out = [WEBSITE_INVENTORY_URL]
    return out


def is_grillz_intent(message_text: str) -> bool:
    text = (message_text or "").lower()
    grill_terms = [
        "grill", "grillz", "grills", "teeth", "tooth", "top 6", "top six", "bottom 6", "bottom six",
        "parrilla", "diente", "dientes",
    ]
    return any(term in text for term in grill_terms)


def is_chain_intent(message_text: str) -> bool:
    text = (message_text or "").lower()
    chain_terms = [
        "chain", "chains", "cadena", "cadenas", "necklace", "cubana", "rope", "figaro", "tennis chain",
    ]
    return any(term in text for term in chain_terms)


def has_chain_reference_details(message_text: str) -> bool:
    text = (message_text or "").lower()
    detail_terms = [
        "cubana", "rope", "figaro", "franco", "tennis", "miami", "hollow", "solid",
        "white gold", "yellow gold", "rose gold", "14 karat", "18 karat", "10 karat",
        "inch", "inches", "mm", "width", "length", "budget", "price", "carat",
    ]
    return any(term in text for term in detail_terms) or bool(re.search(r"\b\d{1,2}(?:\.?\d+)?\s*(?:mm|inch|inches|karat|k)\b", text))


def build_chain_response(message_text: str) -> str:
    """Guide customer to chain links with short follow-up qualification."""
    links = match_inventory_links(message_text, max_links=2)
    links_text = " ".join([f"Link {i+1}: {url}" for i, url in enumerate(links)]) if links else ""

    if has_chain_reference_details(message_text):
        base = "Got you - I can match that chain style and walk you through options on the site."
        follow = "Do you want solid or hollow, and what length/mm?"
    else:
        base = "Got you on chains - what design are you looking for (Cuban, rope, Figaro, tennis, etc.)?"
        follow = "Also send your preferred length and budget so I can narrow it fast."

    response = f"{base} {follow}".strip()
    if links_text:
        response = f"{response} {links_text}".strip()
    return response


def extract_teeth_count(message_text: str) -> int | None:
    text = (message_text or "").lower()
    # Examples: "8 teeth", "6 top", "top 6", "10 tooth"
    patterns = [
        r"\b(\d{1,2})\s*(?:teeth|tooth|dientes|diente)\b",
        r"\b(?:top|bottom|upper|lower)\s*(\d{1,2})\b",
        r"\b(\d{1,2})\s*(?:top|bottom|upper|lower)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            try:
                value = int(match.group(1))
                if 1 <= value <= 28:
                    return value
            except ValueError:
                return None
    return None


def build_grillz_response(message_text: str) -> str:
    """Keep grillz conversations focused on tooth count + website pricing."""
    teeth = extract_teeth_count(message_text)
    options_text = "Most people do even sets like 2, 4, 8, or 10 teeth"
    mold_kit_text = (
        f"I can help you order a mold kit from {MOLD_KIT_URL}"
        if MOLD_KIT_URL else
        "I can help you order a mold kit from our website"
    )
    in_person_text = (
        f"or come in person ({IN_PERSON_URL})"
        if IN_PERSON_URL else
        "or come in person"
    )

    if teeth:
        return (
            f"Got you on {teeth} teeth - pricing is on {GRILLZ_PRICING_URL}; {options_text} if you want to level up, and {mold_kit_text} {in_person_text}."
        )
    return (
        f"How many teeth you want (top, bottom, or both)? Pricing is on {GRILLZ_PRICING_URL}; {options_text}, and {mold_kit_text} {in_person_text}."
    )


def attach_relevant_inventory_links(message_text: str, response_text: str) -> str:
    """Append up to one concise inventory link when customer asks about products/pricing."""
    msg = (message_text or "").lower()
    product_signals = [
        "price", "pricing", "cost", "quote", "ring", "chain", "bracelet", "pendant", "grill", "grillz",
        "inventory", "available", "stock", "shop", "producto", "precio", "cotizacion", "anillo", "cadena",
    ]
    if not any(sig in msg for sig in product_signals):
        return response_text

    links = match_inventory_links(message_text, max_links=1)
    if not links:
        return response_text

    link_text = f"Best link: {links[0]}"
    if link_text in response_text:
        return response_text
    combined = f"{response_text} {link_text}".strip()
    if len(combined) > 260:
        return response_text
    return combined


TEXT_ABBREVIATIONS = {
    "u": "you",
    "ur": "your",
    "r": "are",
    "idk": "i do not know",
    "imo": "in my opinion",
    "imho": "in my humble opinion",
    "tbh": "to be honest",
    "asap": "as soon as possible",
    "pls": "please",
    "pls.": "please",
    "plz": "please",
    "thx": "thanks",
    "ty": "thank you",
    "np": "no problem",
    "btw": "by the way",
    "rn": "right now",
    "tmrw": "tomorrow",
    "lmk": "let me know",
    "hmu": "hit me up",
    "wyd": "what are you doing",
    "wya": "where are you",
    "wsg": "what is good",
    "fr": "for real",
    "frfr": "for real for real",
    "ngl": "not gonna lie",
    "bc": "because",
    "cuz": "because",
    "coz": "because",
    "msg": "message",
    "dm": "direct message",
    "ikr": "i know right",
    "smh": "shaking my head",
    "brb": "be right back",
    "ttyl": "talk to you later",
    "omw": "on my way",
    "nvm": "never mind",
    "bday": "birthday",
    "wtb": "want to buy",
    "iso": "in search of",
    "obo": "or best offer",
    "pymt": "payment",
    "dep": "deposit",
    "sz": "size",
    "avail": "available",
    "eta": "estimated time of arrival",
    "qc": "quality check",
    "pic": "picture",
    "pics": "pictures",
    "vid": "video",
    "vids": "videos",
    # Jewelry-specific shorthand
    "wg": "white gold",
    "yg": "yellow gold",
    "rg": "rose gold",
    "ss": "sterling silver",
    "plat": "platinum",
    "mois": "moissanite",
    "eng": "engagement",
    "pend": "pendant",
    "grillz": "grills",
    "vvs": "very very slightly included",
    "vs": "very slightly included",
    "si": "slightly included",
    "lab": "lab grown",
    "nat": "natural",
    "dia": "diamond",
    # Spanish texting shorthand
    "q": "que",
    "k": "que",
    "xq": "porque",
    "pq": "porque",
    "porq": "porque",
    "pa": "para",
    "xfa": "por favor",
    "tmb": "tambien",
    "tb": "tambien",
    "bn": "bien",
    "dnd": "donde",
    "nd": "nada",
    "mnsj": "mensaje",
    "msj": "mensaje",
    "cotiz": "cotizacion",
    "aprox": "aproximado",
    "disp": "disponible",
    "envio": "shipping",
    "urg": "urgente",
    "ahorita": "right now",
    # Spanish jewelry shorthand
    "oro": "gold",
    "plata": "silver",
    "anillo": "ring",
    "cadena": "chain",
    "dije": "pendant",
    "grills": "grills",
    "quilates": "carat",
}


def normalize_text_abbreviations(message_text: str) -> str:
    """Expand common text-message shorthand before sending to the model."""
    if not message_text:
        return ""

    normalized_text = message_text

    # Normalize common jewelry compact formats before token-level expansion.
    normalized_text = re.sub(r"\b(10|14|18|22|24)k\b", r"\1 karat", normalized_text, flags=re.IGNORECASE)
    normalized_text = re.sub(r"\b(\d+(?:\.\d+)?)\s?cts?\b", r"\1 carat", normalized_text, flags=re.IGNORECASE)
    normalized_text = re.sub(r"\b(\d+(?:\.\d+)?)\s?ct\b", r"\1 carat", normalized_text, flags=re.IGNORECASE)

    tokens = normalized_text.split()
    normalized_tokens = []

    for token in tokens:
        # Keep surrounding punctuation while normalizing the core token.
        prefix = re.match(r"^[^a-zA-Z0-9]*", token).group(0)
        suffix = re.search(r"[^a-zA-Z0-9]*$", token).group(0)
        core = token[len(prefix): len(token) - len(suffix) if suffix else len(token)]

        key = core.lower()
        replacement = TEXT_ABBREVIATIONS.get(key, core)
        normalized_tokens.append(f"{prefix}{replacement}{suffix}")

    return " ".join(normalized_tokens)


async def send_facebook_message_with_random_delay(recipient_id: str, message_text: str) -> bool:
    """Send with a random 1-3 minute delay to feel natural."""
    if should_respond_immediately(recipient_id):
        logger.info("Burst detected for %s; sending immediate response", recipient_id)
        return await send_facebook_message(recipient_id, message_text)

    min_delay = max(0, RESPONSE_DELAY_MIN_SECONDS)
    max_delay = max(min_delay, RESPONSE_DELAY_MAX_SECONDS)
    delay_seconds = random.randint(min_delay, max_delay)
    logger.info("Delaying response to %s by %ss", recipient_id, delay_seconds)
    await asyncio.sleep(delay_seconds)
    return await send_facebook_message(recipient_id, message_text)


def register_incoming_message(sender_id: str) -> None:
    """Track inbound message timestamps per sender for burst detection."""
    if not sender_id:
        return

    now = time.time()
    cutoff = now - max(1, DM_BURST_WINDOW_SECONDS)
    bucket = recent_inbound_by_sender.get(sender_id, [])
    bucket = [ts for ts in bucket if ts >= cutoff]
    bucket.append(now)
    recent_inbound_by_sender[sender_id] = bucket


def should_respond_immediately(sender_id: str) -> bool:
    """Immediate reply when user sends multiple messages in a short burst."""
    if not sender_id:
        return False

    now = time.time()
    cutoff = now - max(1, DM_BURST_WINDOW_SECONDS)
    bucket = recent_inbound_by_sender.get(sender_id, [])
    bucket = [ts for ts in bucket if ts >= cutoff]
    recent_inbound_by_sender[sender_id] = bucket
    return len(bucket) >= max(2, DM_BURST_THRESHOLD)


async def process_incoming_message(sender_id: str, message_text: str) -> None:
    """Process a single incoming DM outside webhook response timing."""
    current_task = asyncio.current_task()
    try:
        # Owner-only real-time runtime editing with explicit confirmation.
        if runtime_editor and is_owner_sender(sender_id):
            if runtime_editor.get_setting("realtime_edit_permissions", True):
                handled, owner_reply = runtime_editor.handle_owner_message(sender_id, message_text)
                if handled:
                    final_owner_reply = sanitize_dm_response(owner_reply)
                    logger.info("Final outgoing DM to %s: %s", sender_id, final_owner_reply)
                    await send_facebook_message(sender_id, final_owner_reply)
                    logger.info("Processed owner runtime edit flow for %s", sender_id)
                    return

        normalized_message = normalize_text_abbreviations(message_text)
        if normalized_message != message_text:
            logger.info("Normalized message for %s: %s -> %s", sender_id, message_text, normalized_message)

        history = get_or_create_conversation(sender_id)
        is_first_message = len(history) == 0

        if is_first_message and is_greeting_only_message(message_text):
            response_text = build_first_intro(message_text)
        elif is_grillz_intent(normalized_message):
            response_text = build_grillz_response(normalized_message)
        elif is_chain_intent(normalized_message):
            response_text = build_chain_response(normalized_message)
        else:
            response_text = await generate_response(normalized_message, sender_id=sender_id)
            response_text = pick_short_context_sentence(message_text, response_text)

        response_text = attach_relevant_inventory_links(normalized_message, response_text)

        logger.info("Final outgoing DM to %s: %s", sender_id, response_text)
        await send_facebook_message_with_random_delay(sender_id, response_text)
        store_conversation_turn(sender_id, normalized_message, response_text)
        logger.info("Response sent to %s", sender_id)
    except asyncio.CancelledError:
        logger.info("Canceled pending response task for %s", sender_id)
        raise
    except Exception as exc:
        logger.error("Error in async message processing for %s: %s", sender_id, exc, exc_info=True)
    finally:
        existing = pending_response_tasks.get(sender_id)
        if existing is current_task:
            pending_response_tasks.pop(sender_id, None)


def build_runtime_system_prompt() -> str:
    """Build the current system prompt including fresh personality deltas from new videos."""
    prompt = RAJ_SYSTEM_PROMPT

    if runtime_editor:
        prompt = f"{prompt}\n\n---\n{runtime_editor.get_prompt_appendix()}"

    if not video_updater:
        return prompt

    delta = video_updater.get_runtime_delta_text(max_chars=6000)
    if not delta:
        return prompt

    return (
        f"{prompt}\n\n"
        "---\n"
        "LATEST VOICE DELTAS FROM NEW VIDEOS\n"
        "Apply these as incremental adjustments to the base voice.\n\n"
        f"{delta}"
    )


def _check_admin_key(request: Request) -> None:
    if not ADMIN_API_KEY:
        return
    incoming = request.headers.get("x-admin-key", "")
    if incoming != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key")


def _pid_is_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _acquire_sync_lock() -> bool:
    global sync_lock_fd

    if sync_lock_fd is not None:
        return True

    while True:
        try:
            sync_lock_fd = os.open(SYNC_LOCK_PATH, os.O_CREAT | os.O_EXCL | os.O_RDWR)
            os.write(sync_lock_fd, str(os.getpid()).encode("utf-8"))
            return True
        except FileExistsError:
            try:
                with open(SYNC_LOCK_PATH, "r", encoding="utf-8") as handle:
                    existing_pid = int((handle.read() or "0").strip() or "0")
            except Exception:
                existing_pid = 0

            if existing_pid and _pid_is_alive(existing_pid):
                return False

            try:
                os.remove(SYNC_LOCK_PATH)
            except FileNotFoundError:
                pass


def _release_sync_lock() -> None:
    global sync_lock_fd

    if sync_lock_fd is None:
        return

    try:
        os.close(sync_lock_fd)
    finally:
        sync_lock_fd = None

    try:
        os.remove(SYNC_LOCK_PATH)
    except FileNotFoundError:
        pass


async def _run_personality_sync_once(max_new_videos: int) -> dict:
    return await asyncio.to_thread(video_updater.sync_once, max_new_videos=max_new_videos)


async def _personality_sync_manager() -> None:
    try:
        logger.info("Running startup personality sync from channel videos...")
        startup_result = await _run_personality_sync_once(max_new_videos=5)
        logger.info("Startup sync result: %s", startup_result)

        await personality_sync_loop()
    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.error("Personality sync manager failed: %s", e, exc_info=True)


async def personality_sync_loop() -> None:
    """Background loop: keeps Raj updated when new channel videos are posted."""
    if not video_updater or not video_updater.enabled():
        logger.info("Video personality sync loop not started (missing channel config).")
        return

    while True:
        try:
            result = await _run_personality_sync_once(max_new_videos=3)
            logger.info("Video personality sync result: %s", result)
        except Exception as e:
            logger.error("Video personality sync failed: %s", e, exc_info=True)

        refresh_minutes = PERSONALITY_REFRESH_MINUTES
        if runtime_editor:
            refresh_minutes = int(runtime_editor.get_setting("personality_refresh_minutes", PERSONALITY_REFRESH_MINUTES))

        await asyncio.sleep(max(refresh_minutes, 5) * 60)


# ============================================================================
# FACEBOOK WEBHOOK HANDLERS
# ============================================================================

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "service": "Raj Assistant - Mo The Jeweler Bot",
        "version": "2.0"
    }


@app.get("/webhook/facebook")
async def verify_facebook_webhook(request: Request):
    """
    Facebook webhook verification endpoint.
    Required for Facebook to confirm our webhook is legitimate.
    """
    verify_token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    
    if verify_token == FACEBOOK_WEBHOOK_VERIFY_TOKEN:
        logger.info("Webhook verified successfully")
        return Response(content=challenge, media_type="text/plain")
    else:
        logger.error("Webhook verification failed - invalid token")
        raise HTTPException(status_code=403, detail="Invalid verification token")


@app.post("/webhook/facebook")
async def handle_facebook_webhook(request: Request):
    """
    Handle incoming Facebook messages.
    Receives webhook data, extracts message, generates response via Claude, sends back.
    """
    try:
        data = await request.json()
        logger.info(f"Received webhook event: {json.dumps(data, indent=2)}")
        
        # Verify it's a message event from a page we manage
        if data.get("object") != "page":
            return {"status": "ok"}
        
        # Process each entry in the webhook
        for entry in data.get("entry", []):
            for messaging_event in entry.get("messaging", []):
                sender_id = messaging_event.get("sender", {}).get("id")
                recipient_id = messaging_event.get("recipient", {}).get("id")
                
                # Handle incoming message
                if messaging_event.get("message"):
                    message_text = messaging_event["message"].get("text")
                    
                    if message_text:
                        logger.info(f"Message from {sender_id}: {message_text}")
                        register_incoming_message(sender_id)

                        # Keep only newest pending response per sender.
                        pending = pending_response_tasks.get(sender_id)
                        if pending and not pending.done():
                            pending.cancel()

                        task = asyncio.create_task(process_incoming_message(sender_id, message_text))
                        pending_response_tasks[sender_id] = task
        
        return {"status": "ok"}
    
    except Exception as e:
        logger.error(f"Error handling webhook: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}


# ============================================================================
# MESSAGE GENERATION
# ============================================================================

async def generate_response(user_message: str, sender_id: str | None = None) -> str:
    """
    Generate a response using Claude with Raj's personality system prompt.
    
    Args:
        user_message: The incoming customer message
    
    Returns:
        Response text in Mo's voice
    """
    try:
        runtime_system_prompt = build_runtime_system_prompt()
        style_guardrails = (
            "Reply in Mo's personal voice and style. "
            "Reply in the same language as the customer message (English or Spanish). "
            "If the customer uses mixed Spanglish, you can reply in natural mixed Spanglish. "
            "Do not repeat greeting/opening lines in follow-up messages. "
            "Keep replies extremely short and simple: one short sentence whenever possible, two max. "
            "Keep conversation flowing naturally. "
            "For grill/grillz requests, focus on tooth count, top/bottom scope, and direct pricing from website. "
            "Do not mention mold kits unless the customer explicitly asks about mold kits. "
            "Do not mention your name or identity and do not say you are Raj or Mo."
        )
        response = create_message_with_model_fallback(
            client,
            model=ANTHROPIC_MODEL,
            max_tokens=1024,
            system=f"{runtime_system_prompt}\n\n---\n{style_guardrails}",
            messages=build_conversation_messages(sender_id, user_message)
        )
        
        # Extract response text
        response_text = response.content[0].text
        logger.info(f"Generated response: {response_text[:100]}...")
        
        return response_text
    
    except Exception as e:
        logger.error(f"Error generating response: {str(e)}", exc_info=True)
        # Fallback response
        return "My boy, got you. Hit the DM directly and we'll hook you up. Let's run some numbers. 🔥"


# ============================================================================
# FACEBOOK API
# ============================================================================

async def send_facebook_message(recipient_id: str, message_text: str) -> bool:
    """
    Send a message back to the Facebook user via Facebook API.
    
    Args:
        recipient_id: Facebook user ID
        message_text: Message content to send
    
    Returns:
        True if sent successfully, False otherwise
    """
    # Facebook Messenger Send API endpoint
    url = "https://graph.facebook.com/v18.0/me/messages"
    
    headers = {
        "Content-Type": "application/json"
    }
    
    payload = {
        "recipient": {
            "id": recipient_id
        },
        "message": {
            "text": message_text
        },
        "access_token": FACEBOOK_PAGE_ACCESS_TOKEN
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        logger.info(f"Message sent successfully to {recipient_id}")
        return True
    except Exception as e:
        logger.error(f"Error sending message to Facebook: {str(e)}")
        return False


@app.post("/admin/personality/sync")
async def admin_sync_personality(request: Request):
    """Manually trigger sync from newly posted channel videos."""
    _check_admin_key(request)
    if not video_updater:
        return {"status": "disabled", "reason": "updater_not_available"}

    result = video_updater.sync_once(max_new_videos=5)
    return result


@app.get("/admin/personality/status")
async def admin_personality_status(request: Request):
    """Show auto-update configuration and latest sync metadata."""
    _check_admin_key(request)
    if not video_updater:
        return {"status": "disabled", "reason": "updater_not_available"}

    state = video_updater.load_state()
    return {
        "status": "ok",
        "enabled": video_updater.enabled(),
        "refresh_minutes": PERSONALITY_REFRESH_MINUTES,
        "rss_url": video_updater.rss_url,
        "processed_video_count": len(state.get("processed_video_ids", [])),
        "last_sync_at": state.get("last_sync_at"),
        "last_success_at": state.get("last_success_at"),
    }


@app.get("/admin/voice/status")
async def admin_voice_status(request: Request):
    """Show current Raj voice provider readiness."""
    _check_admin_key(request)
    if not voice_synth:
        return {"status": "disabled", "reason": "voice_synth_unavailable"}
    return {"status": "ok", "voice": voice_synth.status()}


@app.get("/admin/runtime/status")
async def admin_runtime_status(request: Request):
    """Show runtime-edit settings, learned habits, and pending confirmations."""
    _check_admin_key(request)
    if not runtime_editor:
        return {"status": "disabled", "reason": "runtime_editor_unavailable"}

    return {
        "status": "ok",
        "owner_ids_configured": len(OWNER_FACEBOOK_IDS),
        "runtime": runtime_editor.get_status(),
    }


# ============================================================================
# TEST ENDPOINT (for manual testing)
# ============================================================================

@app.post("/test/message")
async def test_message(request: Request):
    """
    Test endpoint to verify Raj responds in Mo's voice.
    
    Usage:
        curl -X POST http://localhost:8000/test/message \
        -H "Content-Type: application/json" \
        -d '{"message": "Hey, what kind of grillz do you make?"}'
    """
    try:
        data = await request.json()
        user_message = data.get("message", "")
        
        if not user_message:
            raise HTTPException(status_code=400, detail="Message field required")
        
        response = await generate_response(user_message)
        return {
            "user_message": user_message,
            "raj_response": response
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in test endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/test/voice")
async def test_voice(request: Request):
    """Generate Raj text response and synthesize it to voice audio."""
    if not voice_synth:
        raise HTTPException(status_code=503, detail="Voice synth module unavailable")

    try:
        data = await request.json()
        user_message = (data.get("message") or "").strip()

        if not user_message:
            raise HTTPException(status_code=400, detail="Message field required")

        raj_text = await generate_response(user_message)
        audio_bytes, content_type = voice_synth.synthesize(raj_text)

        return Response(
            content=audio_bytes,
            media_type=content_type,
            headers={
                "Content-Disposition": 'inline; filename="raj-response.mp3"',
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in voice test endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# CONVERSATION HISTORY (for future multi-turn support)
# ============================================================================

# This is a placeholder for future conversation persistence
# In production, you'd want to store conversations in PostgreSQL
conversation_history = {}


def get_or_create_conversation(user_id: str):
    """Get conversation history for user, or create new one"""
    if user_id not in conversation_history:
        conversation_history[user_id] = []
    return conversation_history[user_id]


def build_conversation_messages(user_id: str | None, latest_user_message: str, max_turns: int = 6):
    """Build recent message window for continuity in DMs."""
    if not user_id:
        return [{"role": "user", "content": latest_user_message}]

    history = get_or_create_conversation(user_id)
    recent = history[-(max_turns * 2):] if history else []
    messages = []
    for item in recent:
        role = item.get("role")
        content = (item.get("content") or "").strip()
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": latest_user_message})
    return messages


def store_conversation_turn(user_id: str, user_message: str, assistant_message: str, max_turns: int = 12) -> None:
    """Persist latest turn for better follow-up responses."""
    history = get_or_create_conversation(user_id)
    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": assistant_message})

    max_items = max_turns * 2
    if len(history) > max_items:
        del history[:-max_items]


# ============================================================================
# STARTUP/SHUTDOWN
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Log startup"""
    global sync_task
    logger.info("🔥 Raj Assistant starting up...")
    logger.info(f"API Key configured: {bool(ANTHROPIC_API_KEY)}")
    logger.info(f"Facebook tokens configured: {bool(FACEBOOK_PAGE_ACCESS_TOKEN and FACEBOOK_WEBHOOK_VERIFY_TOKEN)}")
    logger.info(f"System prompt loaded: {len(RAJ_SYSTEM_PROMPT)} characters")
    logger.info("Owner IDs configured: %s", len(OWNER_FACEBOOK_IDS))
    if voice_synth:
        logger.info("Voice provider status: %s", voice_synth.status())

    if video_updater and video_updater.enabled():
        if _acquire_sync_lock():
            sync_task = asyncio.create_task(_personality_sync_manager())
            logger.info("Background personality sync leader started (%s min).", PERSONALITY_REFRESH_MINUTES)
        else:
            logger.info("Skipping personality sync startup in this worker; another worker owns the sync loop.")


@app.on_event("shutdown")
async def shutdown_event():
    """Log shutdown"""
    global sync_task
    if sync_task:
        sync_task.cancel()
    _release_sync_lock()
    logger.info("🔥 Raj Assistant shutting down...")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    # Get PORT from environment or default to 8000
    port = int(os.getenv("PORT", 8000))
    
    # Run server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
