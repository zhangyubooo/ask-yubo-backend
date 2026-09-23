"""
Ask Yubo — backend for the chat box on https://zhangyubooo.github.io/about.html

Flow:  browser (GitHub Pages)  --POST /chat-->  this Flask app (Render)  -->  Groq API
The Groq API key lives only here, in an environment variable.

(First version used Google Gemini; Google blocked the new project with a 403
"project has been denied access", so the AI call was switched to Groq. Only
this file's AI call changed — the /chat contract, and so the frontend, did not.)
"""

import os
import time
from collections import defaultdict, deque
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS
import groq
from werkzeug.middleware.proxy_fix import ProxyFix


# ---------------------------------------------------------------------------
# 1. Configuration
#    Everything that might change between "my laptop" and "Render" is read from
#    environment variables. Locally they come from the .env file (never
#    committed); on Render they are typed into the dashboard.
# ---------------------------------------------------------------------------

load_dotenv()  # reads .env if it exists; does nothing on Render

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b")

# Websites allowed to call this backend from a browser (CORS whitelist).
# The two localhost entries are for testing the frontend on my own machine.
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "ALLOWED_ORIGINS",
        "https://zhangyubooo.github.io,http://localhost:8000,http://127.0.0.1:8000",
    ).split(",")
    if origin.strip()
]

MAX_MESSAGE_CHARS = 500      # longest single message a visitor may send
MAX_HISTORY_ITEMS = 12       # only the last 12 messages (6 back-and-forths) are sent to the AI
MAX_HISTORY_ITEM_CHARS = 2000
RATE_LIMIT_REQUESTS = 10     # each visitor (IP address) gets at most 10 messages...
RATE_LIMIT_WINDOW = 60       # ...per 60 seconds

# The persona ("you are Yubo...") lives in its own file so it can be edited
# without touching code.
SYSTEM_PROMPT = (Path(__file__).parent / "persona.md").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 2. App setup
# ---------------------------------------------------------------------------

app = Flask(__name__)

# Render sits in front of this app as a proxy, so every request looks like it
# comes from Render itself. ProxyFix reads the X-Forwarded-For header Render
# adds, so request.remote_addr becomes the visitor's real IP. Without this the
# rate limit below would lump every visitor together.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)

# CORS: tell browsers that pages from ALLOWED_ORIGINS may read our responses.
# (Scripts and curl ignore CORS entirely — that's why rate limiting exists too.)
CORS(app, origins=ALLOWED_ORIGINS)

# Created once and reused. If the key is missing we still start, so /health
# works and /chat can return a clear error instead of the server crashing.
# timeout: give up on the AI after 30 s. max_retries=1: retry once on a brief hiccup.
client = groq.Groq(api_key=GROQ_API_KEY, timeout=30, max_retries=1) if GROQ_API_KEY else None
if client is None:
    print("WARNING: GROQ_API_KEY is not set — /chat will return 500 until it is.")


# ---------------------------------------------------------------------------
# 3. Helpers
# ---------------------------------------------------------------------------

def error(message, status):
    """Every error leaves this server in the same JSON shape: {"error": "..."}."""
    return jsonify({"error": message}), status


# Rate limiting: remember the timestamps of each IP's recent requests.
# Stored in memory, so it resets when Render restarts the app — fine for a
# portfolio, and it needs no database.
_recent_requests = defaultdict(deque)


def is_rate_limited(ip):
    now = time.time()
    timestamps = _recent_requests[ip]
    while timestamps and now - timestamps[0] > RATE_LIMIT_WINDOW:
        timestamps.popleft()          # forget requests older than the window
    if len(timestamps) >= RATE_LIMIT_REQUESTS:
        return True
    timestamps.append(now)
    return False


def parse_history(raw):
    """
    Validate the conversation the frontend sends back to us.
    Expected: [{"role": "user" | "model", "text": "..."}, ...]
    Returns (list_of_chat_messages, error_message_or_None).
    The frontend says "model"; Groq's format calls the same thing "assistant".
    """
    if raw is None:
        return [], None
    if not isinstance(raw, list):
        return None, "'history' must be a list."

    messages = []
    for item in raw[-MAX_HISTORY_ITEMS:]:
        if not isinstance(item, dict):
            return None, "Each history item must be an object."
        role, text = item.get("role"), item.get("text")
        if role not in ("user", "model") or not isinstance(text, str):
            return None, "Each history item needs role 'user' or 'model' and a text string."
        messages.append({
            "role": "assistant" if role == "model" else "user",
            "content": text[:MAX_HISTORY_ITEM_CHARS],
        })
    return messages, None


# ---------------------------------------------------------------------------
# 4. Endpoints
# ---------------------------------------------------------------------------

@app.get("/")
def index():
    """So opening the Render URL in a browser shows something useful, not a 404."""
    return jsonify({
        "name": "Ask Yubo backend",
        "endpoints": {"GET /health": "wake-up check", "POST /chat": "send a message"},
    })


@app.get("/health")
def health():
    """
    The frontend calls this as soon as the page loads. On Render's free tier the
    first request after a nap takes a while — this gets that wait out of the way
    while the visitor is still reading.
    """
    return jsonify({"status": "ok"})


@app.post("/chat")
def chat():
    # --- 4a. Rate limit ----------------------------------------------------
    if is_rate_limited(request.remote_addr):
        response, status = error("Too many messages — please wait a minute and try again.", 429)
        response.headers["Retry-After"] = str(RATE_LIMIT_WINDOW)
        return response, status

    # --- 4b. Validate input ------------------------------------------------
    data = request.get_json(silent=True)   # None if the body isn't valid JSON
    if not isinstance(data, dict):
        return error("Send a JSON body like {\"message\": \"Hi\"}.", 400)

    message = data.get("message")
    if not isinstance(message, str) or not message.strip():
        return error("Please type a message first.", 400)
    message = message.strip()
    if len(message) > MAX_MESSAGE_CHARS:
        return error(f"Please keep messages under {MAX_MESSAGE_CHARS} characters.", 400)

    history, history_error = parse_history(data.get("history"))
    if history_error:
        return error(history_error, 400)

    if client is None:
        return error("The server is missing its API key.", 500)

    # --- 4c. Ask the AI ---------------------------------------------------
    # Chat format: the persona goes first as a "system" message, then the
    # conversation so far, then the new question.
    messages = (
        [{"role": "system", "content": SYSTEM_PROMPT}]
        + history
        + [{"role": "user", "content": message}]
    )
    try:
        result = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            temperature=0.4,   # lower = sticks closer to the facts in persona.md
            max_completion_tokens=2048,
        )
    except groq.APIStatusError as exc:
        # The AI service answered with an error code. Log the details for me
        # (visible in Render's Logs tab); give the visitor a short, safe message.
        print(f"Groq API error {exc.status_code}: {exc.message}")
        if exc.status_code == 429:
            return error("Ask Yubo has hit its free usage limit — please try again later.", 503)
        return error("The AI service had a problem. Please try again.", 502)
    except Exception as exc:  # timeouts, network problems, anything unexpected
        print(f"Unexpected error calling Groq: {exc!r}")
        return error("Couldn't reach the AI service. Please try again.", 502)

    reply = (result.choices[0].message.content or "").strip()
    if not reply:  # e.g. the model returned nothing usable
        return error("I couldn't come up with an answer to that — try rephrasing?", 502)

    # --- 4d. Success -------------------------------------------------------
    return jsonify({"reply": reply})


# Unknown URLs and wrong methods also answer in JSON, so the frontend never has
# to deal with an HTML error page.
@app.errorhandler(404)
def not_found(_):
    return error("Not found.", 404)


@app.errorhandler(405)
def method_not_allowed(_):
    return error("Method not allowed.", 405)


# ---------------------------------------------------------------------------
# 5. Local development entry point
#    `python app.py` runs Flask's built-in dev server on http://127.0.0.1:5001
#    (5001, not 5000: macOS's AirPlay Receiver already uses port 5000).
#    On Render this block is skipped — Render runs `gunicorn app:app` instead.
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 5001)), debug=True)
