# Multi-Agent Customer Support (POC) — Async Human-in-the-Loop Refunds

A Test teaching-oriented, POC-level multi-turn conversational support bot. It
gathers information over several turns, compacts the conversation into a
small structured ticket, routes to a Billing or Refunds specialist, and
sends **every** refund request to an asynchronous human-review queue — the
customer is never blocked waiting for a human to review anything.

## 1. Prerequisites

- Python 3.11+
- An OpenAI API key (or any provider/model LiteLLM supports — see `LLM_MODEL` below)

## 2. Setup

```bash
cd project4_multi_agent_customer_support

python3 -m venv .venv

#Mac Users run this command
source .venv/bin/activate    

# Windows users run this command
.venv\Scripts\activate

pip install -r requirements.txt

# Create your .env file then edit the file to set your OPENAI_API_KEY value
cp .env.example .env              
```

## 3. Build the database

The mocked tools read from an embedded SQLite database seeded with a
sample dataset. Build it once before first run:

```bash
python -m db.init_db
```

This creates `data/support.db` from `db/schema.sql` (table definitions) and
`db/seed_data.sql` (12 sample orders, `ORD-1001`..`ORD-1012`, covering a mix
of payment statuses and refund eligibility — see `db/seed_data.sql` for the
exact values). Re-running the command is safe any time you want to reset
to a known-clean dataset — it drops and recreates every table.

If you skip this step, the app bootstraps the database automatically the
first time a tool needs it (`db/connection.py::ensure_initialized`) — but
running it explicitly is the documented, primary path.

## 4. Run the app

```bash
streamlit run streamlit_app.py
```

Open the URL Streamlit prints (typically http://localhost:8501). Use the
sidebar to switch between **Customer Chat** and **Approver Queue**.

Check the file named "conversation.md" to find example conversations.

## 5. Configuration

Everything configurable lives in `config.py` and is overridable via `.env`:

| Variable | Default | Purpose |
|---|---|---|
| `OPENAI_API_KEY` | — | Required; read by LiteLLM, not by our code directly |
| `LLM_MODEL` | `gpt-4o-mini` | Any LiteLLM-supported model string |
| `DB_PATH` | `data/support.db` | Location of the embedded SQLite database |
| `APPROVAL_TURNAROUND_HOURS` | `24` | Cosmetic — used in the "under review" message |

## Where each concept lives

| Concept                          | File(s) |
|-----------------------------------|---------|
| Session (resumable across time)   | `session/session_store.py`, `pipeline/state.py::new_session_state` |
| Conversational memory/history      | `SessionState.conversation_history`, appended to in every node |
| Context compaction                 | `pipeline/compaction.py` |
| Tool usage (DB-backed mocks)        | `tools/mock_tools.py`, `db/` |
| Async human-in-the-loop            | `agents/refunds_agent.py` (files the request) + `pipeline/approval_graph.py` (resolves it) |
| Customer-turn orchestration        | `pipeline/graph.py` |

## Demo script

1. Open **Customer Chat**, send something vague ("I have a problem with my order") — the bot asks a clarifying question.
2. Give an order ID (e.g. `ORD-1003`) and describe the issue — after enough detail, the compacted JSON panel populates.
3. A billing-shaped issue routes to the Billing Agent, which looks up the order in the database and returns invoice/payment-status details in one turn.
4. A refund request (any amount, e.g. `ORD-1006`) routes to the Refunds Agent, which checks DB-backed eligibility and — if eligible — always files a `PendingApproval` and replies that it's under review. The graph run still completes normally; nothing blocks.
5. Try an ineligible order (`ORD-1005` or `ORD-1011`, both seeded as final-sale/past-window) — the bot explains why no refund is possible, no approval is filed.
6. Switch to **Approver Queue**, see the pending request, and Approve or Deny it. This runs a brand-new, independent graph invocation.
7. Go back to **Customer Chat**, re-enter the same session ID — the resolution message is already there, as if it arrived while you were away.
8. **New Session** starts a completely clean session with no leakage from the previous one.

## Deliberate scope decisions

- **No MCP.** Tools here are plain local Python functions
  (`tools/mock_tools.py`) called directly by the specialist agents. MCP
  exists to expose tools to *external* MCP clients — nothing in this POC
  needs that, so adding an MCP server would be indirection with no payoff.
  This is a deliberate decision, not an oversight.
- **Embedded SQLite, read-only tool access.** The mocked tools
  (`lookup_invoice`, `check_payment_status`, `check_refund_eligibility`)
  query a real embedded database (`db/`) instead of fabricating data.
  Every tool opens the database through
  `db.connection.get_read_only_connection()`, which uses SQLite's URI
  `mode=ro` — any `INSERT`/`UPDATE`/`DELETE` attempted through that
  connection fails with `sqlite3.OperationalError`, a real, DB-enforced
  guarantee. Worth being honest about a limitation: SQLite has no
  user/role system, so unlike Postgres there's no per-table `GRANT` to
  lean on. A read-only *connection* is the strongest access control an
  embedded, single-file database offers, and it's enough for this POC —
  only `db/init_db.py` (via `get_admin_connection`) ever opens a
  read-write connection, and nothing at runtime imports it.
- **No refund is ever issued by an agent.** Every eligible refund request,
  regardless of amount, is filed as a `PendingApproval` and goes to manual
  review (`agents/refunds_agent.py`). There is no `issue_refund` tool —
  issuing a refund is purely the outcome of a human clicking Approve in
  the Approver View (`pipeline/approval_graph.py`), never something the
  conversational agent does on its own.
- **No other persistent database.** Session and approval *state*
  (conversation history, compacted tickets, pending approvals) still live
  in module-level dicts (`session/session_store.py`) — only the mocked
  tools' reference data moved into SQLite. Every other module talks to
  session storage only through that file's functions, so swapping in a
  real database later is a one-file change.
- **Async, not blocking, approval.** A naive design would pause the graph
  mid-execution waiting for a human to click Approve/Deny. That's wrong
  here: the approver is a different person, working on their own schedule,
  and the customer should never be stuck staring at a spinner. Instead,
  "pending approval" is just a status value in a `PendingApproval` record —
  the customer-turn graph always runs start-to-finish and returns
  immediately, and the approval is resolved later by a *second*,
  independent graph invocation (`pipeline/approval_graph.py`) triggered from
  the Approver View. The two flows only ever meet through shared storage.
- **No LangGraph `interrupt()`.** Same reasoning as above — pause/resume
  would model the approval as a suspended execution, which contradicts the
  "never block the customer" requirement. Every `invoke()` call in this
  codebase runs to completion.
- **No production hardening.** No PII redaction, no prompt-injection
  detection, no retries/fallback models, no auth. Explicitly out of scope
  for a teaching POC.
