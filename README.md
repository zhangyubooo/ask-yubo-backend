# Ask Yubo — backend

**15-113 HW4 — Backend + Frontend**
Yubo Zhang · Carnegie Mellon University, School of Design

A small Flask service that powers **Ask Yubo**, a floating chat widget on
every page of my portfolio. Visitors ask questions about me and my work, and an AI answers in
my voice, using only what is already published on the site.

| | |
|---|---|
| Backend (Render) | <https://ask-yubo-backend.onrender.com> (try `/health`) |
| Frontend | <https://zhangyubooo.github.io/> — the round button, bottom-right, on every page |
| Project page | <https://zhangyubooo.github.io/ask-yubo.html> — description, decisions, code links |
| Frontend repo | <https://github.com/zhangyubooo/zhangyubooo.github.io> |
| AI model | `openai/gpt-oss-20b` via the Groq API (free tier) |

## Why this needs a backend

My HW3 project (World Oracle) deliberately used only keyless APIs, because
anything in front-end JavaScript is readable by anyone who opens DevTools.
A chatbot needs an AI API key, so it can't run on GitHub Pages alone.
This backend holds the key and is the only thing that talks to the AI.

```
browser (GitHub Pages)  ──POST /chat──▶  Flask on Render  ──(API key)──▶  Groq
                        ◀──{"reply"}───                   ◀──────────────
```

**Why Groq and not Gemini:** the first version called Google Gemini. It worked
once, then Google's abuse checks blocked the brand-new project with
`403 "Your project has been denied access"`, which can't be fixed from code.
I switched the AI call in `app.py` to Groq. Because the frontend only knows
the `/chat` contract (`{message, history}` in, `{reply}` out), **the frontend
didn't change at all** — the backend boundary did its job.

---

## Endpoints

### `GET /health`
Wake-up check. Returns `{"status": "ok"}`.

### `POST /chat`
Send one message plus the conversation so far.

**Request body (JSON)**

| Field | Type | Required | Notes |
|---|---|---|---|
| `message` | string | yes | 1–500 characters after trimming whitespace |
| `history` | array | no | Earlier turns: `[{"role": "user" \| "model", "text": "..."}]`. Only the last 12 items are used. |

**Success — `200`**
```json
{ "reply": "I'm studying Design & Product Management at CMU..." }
```

**Errors** — always `{"error": "<message safe to show the visitor>"}`

| Status | When |
|---|---|
| `400` | Body isn't JSON, message is empty or too long, or `history` is malformed |
| `429` | More than 10 messages in 60 seconds from the same IP (`Retry-After` header is set) |
| `500` | The server has no `GROQ_API_KEY` configured |
| `502` | The AI service returned an error, timed out, or returned an empty reply |
| `503` | The AI service's free-tier limit is used up |

### `GET /`
Short JSON description of the service, so opening the base URL isn't a 404.

---

## How the frontend talks to the backend

The frontend is a self-contained widget in my portfolio repo —
[`ask-yubo.js`](https://github.com/zhangyubooo/zhangyubooo.github.io/blob/main/ask-yubo.js)
and `ask-yubo.css` — added to `index.html`, `about.html` and `play.html` with
two lines each. The script builds a round chat button in the bottom-right
corner; clicking it opens a text-message style panel on the right.

1. **On page load** (and whenever the panel opens) it calls `GET /health`
   without waiting for the result. Render's free tier sleeps after ~15 minutes
   idle and the first request can take up to a minute; this starts the wake-up
   early.
2. **When the visitor sends a message** it calls `POST /chat` with
   `{message, history}`, shows a typing indicator, and disables the send button
   until the answer arrives. After 6 seconds it adds a "waking up the server"
   note.
3. **On `200`** it adds `reply` as a bubble and appends both messages to its
   `history` array for the next request.
4. **On an error status** it fades the visitor's bubble and shows
   "Not delivered — *the `error` text from the JSON*". The message is put back
   in the input so it can be re-sent. If there is no response at all (backend
   asleep or down, 70-second timeout) it says the server couldn't be reached.

The backend is **stateless**: it stores no conversations. The browser keeps the
history — in `sessionStorage`, so the conversation follows the visitor from page
to page within one tab — and sends it back each time. No database, and nothing
is lost when Render restarts.

---

## Running it locally

Requires Python 3.10+.

```bash
git clone https://github.com/zhangyubooo/ask-yubo-backend.git
cd ask-yubo-backend

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env               # then open .env and paste your Groq key
python app.py                      # → http://127.0.0.1:5001
```

Port **5001** is used instead of Flask's default 5000 because macOS's AirPlay
Receiver already occupies 5000.

Test it without any frontend:

```bash
curl http://127.0.0.1:5001/health

curl -X POST http://127.0.0.1:5001/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What are you studying?"}'

# error case: empty message → 400
curl -X POST http://127.0.0.1:5001/chat \
  -H "Content-Type: application/json" -d '{"message": ""}'
```

To test the real frontend against the local backend, serve the portfolio folder
over HTTP (opening the file directly gives it a `null` origin, which CORS
rejects). `ask-yubo.js` picks its backend from the page's address: on
`localhost` / `127.0.0.1` it calls `http://127.0.0.1:5001`, everywhere else it
calls Render — so there is no URL to remember to switch back before pushing.

```bash
cd ../zhangyubooo.github.io
python3 -m http.server 8000        # → http://localhost:8000/ (chat button bottom-right)
```

## Deploying to Render

New → **Web Service** → connect this repo, then:

| Setting | Value |
|---|---|
| Runtime | Python 3 |
| Build command | `pip install -r requirements.txt` |
| Start command | `gunicorn app:app` |
| Instance type | Free |
| Environment variable | `GROQ_API_KEY` = *your key* |

Render sets `PORT` itself and gunicorn binds to it automatically.

---

## Secrets and security

- **The Groq key exists in exactly two places:** a local `.env` file, which
  `.gitignore` keeps out of Git, and Render's Environment settings. It is never
  in this repo and never sent to the browser.
- The key is on Groq's **free plan with no payment method attached**, so even
  if it leaked it could not generate charges — it would only use up the free
  daily limit, and it can be revoked and replaced in the Groq console.
- **CORS** only allows `https://zhangyubooo.github.io` (plus `localhost:8000`
  for testing) to read responses in a browser. CORS is enforced by browsers,
  not servers, so it doesn't stop scripts or `curl` —
- …which is why the backend also **validates every input** (type, length,
  history shape) and **rate-limits by IP** before any AI call is made.
  Render sits behind a proxy, so `ProxyFix` is used to read the visitor's real
  IP from `X-Forwarded-For`.
- The AI service's error details are printed to Render's logs; visitors only see a
  short generic message.
- The persona in `persona.md` contains only information already public on my
  portfolio, and tells the model not to invent facts, so nothing private is
  ever sent to the AI service.

**Known limits:** the rate limiter lives in memory, so it resets when the
service restarts and would not be shared across multiple instances — fine for
one free-tier instance, not for production.

## Files

| File | Purpose |
|---|---|
| `app.py` | The Flask app: config, CORS, validation, rate limit, AI call |
| `persona.md` | System prompt — who "Ask Yubo" is and the facts it may use |
| `requirements.txt` | Pinned Python dependencies |
| `.env.example` | Template for the local `.env` (the real one is git-ignored) |
| `prompt_log.md` | AI tools and key prompts used to build this |
