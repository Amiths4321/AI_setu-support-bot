# Setu — Customer Support Chatbot (Demo)

A working demo of a customer-facing support chatbot for retail banking —
built to showcase what an always-on, first-line support layer could look
like sitting on top of DNS Bank's existing digital channels (the "Do
Mobile Plus" app, internet banking, branch network).

> **This is a sales/portfolio demo, not production software.** All
> customers, accounts, balances, and transactions are synthetically
> generated. No real banking data is used or required.

## Why this demo, why this bank

DNS Bank has already invested in reducing turnaround time on the
back-office side — online KYC, centralised account opening, LOS-based
loan sanctioning. **Setu** picks up the natural customer-facing
counterpart to that investment: a chatbot that handles the high-volume,
low-complexity queries that otherwise tie up branch staff and call
centre lines — balance checks, card blocking, branch timings, cheque
book requests, FAQs — so human staff are freed up for things that
actually need a person.

Specific choices that matter for the pitch:

- **No LLM/API dependency.** Intent recognition is a transparent,
  regex-and-weights engine (see `nlu.py`) — not a call to an external AI
  API. That means zero per-conversation cost, zero data leaving the
  bank's own infrastructure, and a system whose decisions support staff
  can fully audit. (Swapping in an LLM-based NLU later is a deliberate,
  optional upgrade path — not a requirement to get value from this.)
- **Sensitive actions require verification + confirmation.** Blocking or
  unblocking a card always asks for account number, then a verification
  code, then explicit yes/no confirmation before anything changes — never
  a single message away from an irreversible action.
- **Graceful fallback, not a dead end.** Anything the bot doesn't
  recognise falls through to an FAQ search, and failing that, an offer to
  hand off to a human agent — it never just says "I don't understand."

## What it does

A customer chats with **Setu** through a widget (mocked here on top of a
sample DNS Bank homepage). It can:

| Capability | What happens |
|---|---|
| Balance check | Verifies identity (account + phone digits), then returns balance |
| Mini statement | Verifies identity, then returns last 5 transactions |
| Block / unblock card | Verifies identity, confirms intent, then updates card status |
| Cheque book request | Verifies identity, then logs the request |
| Branch locator | Asks for a city if not given, returns matching branches |
| Complaint registration | Collects a description, issues a ticket ID |
| FAQs | Matches free-text questions (hours, documents, interest rates, NEFT/RTGS, minimum balance) |
| Fallback | Offers a human agent handoff when nothing else matches |

## Project structure

```
setu-support-bot/
├── backend/
│   ├── app.py               # FastAPI app: /api/chat, /api/reset, /api/health
│   ├── dialogue_manager.py    # session state machine — the core of this demo
│   ├── nlu.py                 # intent classification + entity extraction
│   ├── mock_data.py           # synthetic customers, branches, FAQ knowledge base
│   └── requirements.txt
└── frontend/
    ├── index.html             # mock bank homepage + chat widget
    ├── style.css
    └── app.js                 # widget open/close, send/receive, quick replies
```

## Running it locally

**1. Backend**
```bash
cd backend
pip install -r requirements.txt
uvicorn app:app --reload --port 8001
```

**2. Frontend** (separate terminal)
```bash
cd frontend
python3 -m http.server 8085
```

Then open **http://localhost:8085** and click the chat launcher
(bottom-right). The widget talks to `http://127.0.0.1:8001` by default —
change the "API base" field inside the chat panel if you run the backend
elsewhere.

No database, no API keys, no external services required.

## Try these in the demo

- `hi` → see the greeting and quick-reply menu
- `block my card` → walks through account number → phone verification →
  confirm → done
- `find a branch in Thane`
- `what documents do i need to open an account`
- Click **↺** in the chat header to reset the conversation mid-demo

Sample test accounts (for the verification step):

| Account number | Phone (last 4) | Name |
|---|---|---|
| DNS4512152591 | 4821 | Rohan Shah |
| DNS9366091555 | 9012 | Priya Joshi |
| DNS2834882395 | 5567 | Suresh Pawar (card already blocked) |

## What this demo intentionally does not cover

Scoped for a sales conversation, not a finished product. It doesn't
include: persistence/database storage (sessions reset if the backend
restarts), authentication beyond the demo verification flow, integration
with the actual core banking system, multi-language support (Marathi/
Hindi, which would matter a great deal for this customer base), or a
human-agent handoff that actually reaches anyone. Those are the natural
next-conversation talking points.

## License

MIT — see `LICENSE`.
