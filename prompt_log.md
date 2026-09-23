# Prompt log — Ask Yubo backend

## Tools

- **Claude (Anthropic)**, in the Claude desktop app (Cowork mode) — choosing
  the project, explaining the architecture, writing the backend, README, and
  frontend, and troubleshooting Google Cloud setup.
- **Groq API** (`openai/gpt-oss-20b`) — the model the finished backend calls
  at runtime. Not used to write code. (Google Gemini was the first choice; see 6.)

## Key prompts

Originally written in Chinese; translated here.

1. **Choosing the idea**
   > "Based on these requirements, what do you think would be best for HW4?"
   > *(pasted the full HW4 spec)*

   Claude suggested an "Ask Yubo" chatbot on my portfolio over a Forbes
   Crossing leaderboard, because a chatbot needs only one secret and no
   database — the parts past students found hardest. I agreed.

2. **Picking a free AI API**
   > "OK, let's do the Ask Yubo chat box. I didn't use an AI API in HW3 — find
   > a free one."

   Compared Gemini (free tier, no card) with Groq; chose Gemini.

3. **Concepts before code**
   > "OK" *(to: explain the overall architecture first while I get the key)*

   Claude explained the request path, why the key must stay on the server,
   environment variables, ports/localhost, CORS (and that it does not protect
   the key), stateless history, and Render's cold starts.

4. **Getting a key** — several rounds of screenshots when AI Studio failed to
   create a project, the Cloud Console credentials wizard offered OAuth /
   service accounts, and Google required the API key to be bound to a service
   account. Ended with a key restricted to the Gemini API, no billing enabled.

5. **Building it**
   > "OK, the key is created."

   Claude wrote `app.py`, `persona.md`, and this repo's docs, and tested every
   error path (empty / too long / malformed input, rate limit, AI quota and
   timeout, missing key) against a mocked AI client before I ran it with
   the real key.

6. **Debugging the first real failure**
   > *(screenshot of the chat showing "The AI service had a problem")*
   > *(then a screenshot of the backend terminal)*

   The backend log showed `Gemini API error 403: Your project has been denied
   access`. Curl had worked minutes earlier, so the code was fine — Google had
   flagged the new project. Rather than fight an account review before the
   deadline, we switched `app.py` to Groq (the backup chosen in step 2). The
   `/chat` request and response stayed the same, so the frontend didn't change.

7. **First live test caught a made-up fact**
   > *(screenshot of curl against the Render URL)*

   The deployed backend answered correctly but added that my degree is "a
   five-year program" — not in the persona, and wrong (2025–2029 is four
   years). Fix: stated the degree length explicitly in `persona.md`, added a
   rule against embellishing programs/projects, and lowered `temperature`
   from 0.7 to 0.4 so the model sticks closer to the facts.

## Decisions I made / changed

- Keep the frontend on GitHub Pages and the backend on Render (two origins,
  so CORS is required) rather than serving both from Render.
- Persona lives in `persona.md`, not in code, so I can rewrite it in my own
  words without touching Python.
- *(add your own edits here as you make them)*
