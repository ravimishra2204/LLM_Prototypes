"""Concept: Info-Gathering Node — the first LLM call in the customer-turn
graph (Section 4).

Job of this node, and *only* this node: look at the full conversation and
decide whether there's enough information to act. If not, produce a single
clarifying question and stop the turn there. It deliberately does NOT
produce the structured `CompactedTicketInfo` — that's the Context
Compaction node's job (pipeline/compaction.py). Keeping these separate is
the teaching point: "enough info to proceed?" and "what exactly is the
structured ticket?" are different questions, and conflating them into one
LLM call makes both harder to prompt for and to test.
"""
from llm.client import complete_json
from pipeline.state import SessionState, now_iso

SYSTEM_PROMPT = """You are the info-gathering step of a customer support bot.

Read the full conversation so far and decide whether enough information has
been gathered to route this ticket to a specialist team. Do not solve the
issue yourself — only judge completeness and, if incomplete, ask ONE
clarifying question.

Minimum information required, depending on what the issue seems to be about:
- Billing issues: what the issue is about, and an order ID.
- Refund requests: what the issue is about, an order ID, and the rupee
  amount the customer wants refunded.
- Technical/account issues or anything else: a clear description of the
  issue is enough on its own.

If the customer has provided enough detail for their apparent issue type,
mark it complete even if some of the above fields are technically implicit
(e.g. they only have one order and it's obvious which one they mean).

Respond with ONLY a JSON object, no markdown fences, no commentary:
{
  "info_complete": true | false,
  "clarifying_question": string | null   // required if info_complete is false, else null
}
"""


def _format_transcript(history: list) -> str:
    lines = [f"{m['role']}: {m['content']}" for m in history]
    return "\n".join(lines)


def run(state: SessionState) -> SessionState:
    transcript = _format_transcript(state["conversation_history"])
    result = complete_json(SYSTEM_PROMPT, transcript)

    info_complete = bool(result.get("info_complete", False))

    if not info_complete:
        question = result.get("clarifying_question") or (
            "Could you share a bit more detail so I can help with that?"
        )
        state["conversation_history"].append(
            {"role": "assistant", "content": question, "timestamp": now_iso()}
        )

    state["awaiting_clarification"] = not info_complete
    return state
