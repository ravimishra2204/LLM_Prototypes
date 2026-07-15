"""Thin wrapper around LiteLLM — the *only* place in the codebase that calls
`litellm.completion(...)`.

Concept: every model call in this POC (both the Info-Gathering node and the
Context Compaction node) goes through `complete_json`, and the model name
comes from config.py, not a string literal buried in a node. If you ever
swap providers (OpenAI -> Anthropic -> a local model via Ollama), this is
the one function whose behavior you're relying on, and config.py is the one
line you'd change.

No retries, no fallback models, no streaming — this is a POC, and adding
that machinery here would obscure the teaching point rather than help it.
"""
import json

import litellm

from config import LLM_MODEL


def complete_json(system_prompt: str, user_content: str, temperature: float = 0.0) -> dict:
    """Call the LLM and parse its reply as a JSON object.

    Both the info-gathering and compaction nodes ask the model to respond
    with *only* a JSON object (no prose, no markdown fences) — this helper
    is what turns that raw string back into a Python dict.
    """
    response = litellm.completion(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        temperature=temperature,
        response_format={"type": "json_object"},
    )
    raw = response.choices[0].message.content
    return json.loads(raw)
