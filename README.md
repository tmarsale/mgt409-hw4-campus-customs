# Campus Customs: Yale Apparel Store with an AI Shopping Assistant

**MGT 409 · AI Foundations for Managers · Homework 4**

Campus Customs is a working online store for Yale apparel. Customers can browse 102 products, create an account, and chat with an **AI shopping assistant**. The assistant looks up real prices and live stock, shows matching products on the page, understands vague requests ("something cozy") and follow-up questions ("Does it come in blue?"), and remembers signed-in customers' conversations.

| Part | Technology | Folder |
|---|---|---|
| Website | React 19 + TypeScript + Vite 8 | [`hw4/frontend`](hw4/frontend) |
| Backend API | FastAPI (Python 3.12) | [`hw4/backend`](hw4/backend) |
| AI agent | PydanticAI 2.43 with `gpt-5.6-luna` through Portkey, plus 4 read-only tools | [`hw4/backend/agent.py`](hw4/backend/agent.py), [`tools.py`](hw4/backend/tools.py), [`models.py`](hw4/backend/models.py), [`prompts/prompt.md`](hw4/backend/prompts/prompt.md) |
| Audit trail | Append-only JSON log of every agent run | [`hw4/backend/audit.py`](hw4/backend/audit.py) → [`hw4/output/audit_trail.json`](hw4/output/audit_trail.json) |

## Documentation and deliverables

| File | What it is |
|---|---|
| [`hw4/AI_prompts.md`](hw4/AI_prompts.md) | Every prompt used, Problems 1–13, with follow-ups |
| [`hw4/output/harness.md`](hw4/output/harness.md) | **Start here.** Part A: the full system guide (architecture, running it, models, tools, Pydantic models, safety rules, audit trail, limits). Part B: build history. |
| [`hw4/output/usability.md`](hw4/output/usability.md) | Problem 9: four usability improvements and why they help |
| [`hw4/output/design.md`](hw4/output/design.md) | Problem 10: the premium navy-and-cream redesign |
| [`hw4/output/app_check.html`](hw4/output/app_check.html) | Problem 11: live app check with screenshots (download the repo and open the file in a browser) |
| [`hw4/output/audit_trail.json`](hw4/output/audit_trail.json) | Problem 12: real agent activity (tools, arguments, results, stop reasons) |
| [`hw4/output/screenshots/`](hw4/output/screenshots) | 56 screenshots from testing (Problems 3–10) |
| [`hw4/output/app_check_images/`](hw4/output/app_check_images) | Screenshots used by `app_check.html` |

## Folder layout

```
hw4/
├── AI_prompts.md
├── requirements.txt          # Python packages
├── .env.example              # settings template (placeholders only)
├── backend/                  # FastAPI app + PydanticAI agent
│   ├── main.py               # API routes (products, search, chat, history, images)
│   ├── auth.py               # create account / log in / log out
│   ├── agent.py              # the AI agent: model, instructions, answer checks
│   ├── tools.py              # the agent's 4 read-only tools + product search
│   ├── models.py             # Pydantic models
│   ├── history.py            # saved chat history (signed-in customers)
│   ├── audit.py              # audit trail
│   ├── db.py                 # database connections (read-only by default)
│   └── prompts/prompt.md     # the assistant's instructions and safety rules
├── frontend/                 # React website
├── data/                     # ← add the local data pack here (not in Git)
└── output/                   # documentation, screenshots, audit trail
```

## Setup

### 1. Prerequisites

- **Python 3.12** and **Node.js 20.19+ or 22.12+** (tested with Python 3.12.10 and Node 24.21)
- A **Portkey API key** for the AI assistant. Without one, the website still works, but the chat says the assistant is unavailable.
- The course **data pack** (`data.zip`)

### 2. Add the local data pack

The database and product photos are deliberately **not** in this repository. Unzip `data.zip` into `hw4/data/` so you have:

```
hw4/data/campus_customs.db
hw4/data/products/*.jpg      (102 photos)
```

See [`hw4/data/README.md`](hw4/data/README.md).

### 3. Add your settings

Copy the template and put in your own key:

```bash
cp hw4/.env.example hw4/backend/.env
```

Then edit `hw4/backend/.env` and set `PORTKEY_API_KEY`. **Never commit `.env`**; it is already in `.gitignore`.

### 4. Install

```bash
cd hw4
python -m venv .venv
```

Activate it: **Windows** `.venv\Scripts\activate`, **macOS/Linux** `source .venv/bin/activate`. Then:

```bash
pip install -r requirements.txt
```

```bash
cd frontend
npm install
```

*(If the project sits in Dropbox or OneDrive, pause syncing while creating `.venv` and running the installs.)*

## Run

Use two terminals, with the Python environment active in the first.

**Terminal 1: backend** (from `hw4/backend`):

```bash
uvicorn main:app --reload --port 8000
```

Check http://127.0.0.1:8000/api/health. It should return `{"status":"ok","products":102}`.

**Terminal 2: website** (from `hw4/frontend`):

```bash
npm run dev
```

Open **http://localhost:5173**. The website forwards `/api` requests to the backend on port 8000, so both must be running.

**Stop:** `Ctrl+C` in each terminal. If port 8000 or 5173 is still busy, find the process with `netstat -ano | findstr :8000` (Windows) or `lsof -i :8000` (macOS/Linux) and end it.

## Try it

- Open the chat (**Ask our assistant**) and ask: *"How much is the Basic Hoodie Big Yale, and do you have it in XL?"*
- *"What Yale hoodies do you have?"* The matching products appear on the page.
- *"Something cozy for winter"*, then *"Does it come in gray?"*
- Create an account, chat, log out, and log back in. Your conversation is restored.

## Privacy and security

- **No secrets in the repository.** The API key comes from `hw4/backend/.env`, which Git ignores; `.env.example` holds placeholders only.
- **No database or customer data.** `campus_customs.db` and the product photos are excluded by `.gitignore`.
  - Screenshots only show a fictional test account ("Avery Testing").
  - The course test account's password is redacted in the docs.
  - The audit trail stores no message text, customer names, or emails.
- **Read-only AI tools.** The assistant can only look things up. It cannot change orders, prices, stock, or accounts, and the code enforces this, not just the prompt.
- **Passwords** are stored as PBKDF2-HMAC-SHA256 hashes with 120,000 iterations. Login cookies are HttpOnly.

*Campus Customs is a student project for MGT 409 and is not affiliated with Yale University.*
