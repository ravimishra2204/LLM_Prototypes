"""Central place for every knob a student might want to turn.

Nothing here is hardcoded inline elsewhere in the codebase — the LLM model
name and the database path both flow through this module so a reader only
has to look in one place to change POC-wide behavior.
"""
import os

from dotenv import load_dotenv

# Loads OPENAI_API_KEY (and anything else) from a local .env file at import
# time. The key itself is never read directly by our code — litellm picks it
# up from the environment when litellm.completion() is called.
load_dotenv()

# LiteLLM model identifier, e.g. "gpt-4o-mini", "gpt-4o", "claude-sonnet-5".
# See https://docs.litellm.ai/docs/providers for the full naming scheme.
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

# Path to the embedded SQLite database backing the mocked tools (see db/).
DB_PATH = os.getenv("DB_PATH", "data/support.db")

# Purely cosmetic — used in the "your refund is under review" message so the
# customer has an expectation to anchor on. Every eligible refund request
# goes through manual review now, regardless of amount.
APPROVAL_TURNAROUND_HOURS = int(os.getenv("APPROVAL_TURNAROUND_HOURS", "24"))
