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

8. **From a page section to a site-wide floating chat**
   > "I don't want it on the About page. Make it a floating window available
   > anywhere on the site: a chat bubble in the bottom-right corner that opens
   > a chat panel on the right, styled like a text-message thread."

   Claude rebuilt the frontend as a self-contained widget (`ask-yubo.js` +
   `ask-yubo.css`) that each page includes with two lines, with SMS-style
   bubbles, `sessionStorage` so the conversation follows the visitor between
   pages, full-screen layout on phones, and keyboard/screen-reader support.
   The backend didn't change.

9. **UI feedback rounds**
   > "Use this photo as my chat avatar, cropped to my head." →
   > "Make it smaller so my neck / upper body shows." →
   > "Round the corners of the panel on wide screens." →
   > "Add a shadow under the panel so it looks like it's floating."

   Kept on phones: square, shadow-free full-screen panel. The shadow is the
   only one on the site — deliberately, since the chat is the only thing that
   floats above the page.

## Decisions I made / changed

Claude proposed options and explained the trade-offs; these are the calls I
made, and why.

**Scope**
- **A chatbot, not a Forbes Crossing leaderboard.** A leaderboard needs a
  database — the part past students said was hardest. A chatbot needs one
  secret and no storage, so I could spend the time understanding how the
  frontend and backend actually talk. The leaderboard is saved for Project 2.
- **Two repos, two hosts.** Frontend stays on GitHub Pages, backend on Render.
  It means dealing with CORS, but it keeps a clear boundary between the two
  halves, which is the point of the assignment.
- **Persona in its own file (`persona.md`)**, not inside Python, so I can
  rewrite how "I" sound without touching code.

**Platforms**
- **Free API only, no credit card.** I started with Google Gemini.
- **Switching to Groq instead of fighting Google.** Gemini worked once, then
  Google blocked my new project with a 403 that no code change could fix.
  Rather than wait on an account review before the deadline, I switched the
  AI call to Groq. Because the frontend only knows `{message, history}` in and
  `{reply}` out, the frontend didn't change at all.
- **The API key never expires.** The chat is meant to stay on my portfolio, and
  an expiring key would break it silently. The risk is low: there is no
  payment method on the account, and I can revoke the key any time.

**Order of work**
- **Deploy first, polish later — twice.** First I got the plain version
  working end to end (local → Render → live site) before touching the design,
  because the platforms were the risky part. Later, after two rounds of UI
  changes, I pushed again and left the remaining details for later instead of
  holding everything back until it was perfect.
- **Testing the live version found a real bug.** The deployed bot said my
  degree was "a five-year program". I kept the fix small and specific:
  state the real fact, forbid embellishing, lower the temperature.

**Design**
- **A floating chat on every page, not a section on About.** I wanted it
  reachable from anywhere on the site, not only from one page.
- **Styled like a text-message thread,** but kept to my site's black, white
  and grey: my messages in black on the right, the AI in light grey on the left.
- **My own photo as the avatar,** cropped wide enough to show my neck and
  collar rather than just my face.
- **Rounded corners and a shadow on the panel,** even though the rest of the
  site has neither. The chat is the only thing that floats above the page, so
  it's the only thing that gets a shadow. On phones it goes full screen, square,
  with no shadow.
- **A project card and a short project page** so the work is described on the
  portfolio itself, with a real screenshot of the chat as the cover rather than
  an abstract graphic.
