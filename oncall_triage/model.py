"""The model seam: the one place that builds the LLM the agents talk to.

Tests never call ``build_model()`` for a live model - they inject a fake
``BaseLlm`` on the agents directly instead. This module exists so that seam
is a single, obvious function rather than an inline constant.
"""

import os

from google.adk.models.lite_llm import LiteLlm

_DEFAULT_MODEL = "anthropic/claude-haiku-4-5-20251001"


def build_model() -> LiteLlm:
    """Build the LiteLLM-backed model for the triage agents.

    Honours ``TRIAGE_MODEL`` (e.g. to pin a different Claude model or point
    at a different provider through LiteLLM); defaults to Claude Haiku 4.5.
    """
    return LiteLlm(model=os.environ.get("TRIAGE_MODEL", _DEFAULT_MODEL))
