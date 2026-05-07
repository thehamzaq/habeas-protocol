"""Shared Claude grading helper for the perturbation / recode scripts.

Usage (from a script):
    from _claude_grader import grade_judgment

    result = grade_judgment(
        judgment_text=text,
        primitives_json_text=primitives_text,
        model="claude-sonnet-4-5-20250929",
        temperature=0.0,
        prompt_template_path="scripts/ai_grade_prompt_v0_2.txt",
    )

Requires: ANTHROPIC_API_KEY in env, anthropic Python package
(`pip install anthropic`).
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DEFAULT_MODEL = "claude-sonnet-4-5-20250929"
DEFAULT_TEMPERATURE = 0.0
DEFAULT_PROMPT_PATH = ROOT / "scripts" / "ai_grade_prompt_v0_2.txt"
DEFAULT_RUBRIC_PATH = ROOT / "data" / "primitives.json"
PRIM_KEYS = ["pr1", "pr2", "pr3", "pr4", "pr5", "pr6"]
SP_KEYS = ["sp1", "sp2"]


def _client():
    try:
        import anthropic
    except ImportError:
        raise RuntimeError(
            "anthropic package not installed. Run: pip install anthropic"
        )
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set in environment")
    return anthropic.Anthropic(api_key=api_key)


def _build_system_prompt(prompt_template_path: Path,
                         rubric_path: Path = DEFAULT_RUBRIC_PATH) -> str:
    template = Path(prompt_template_path).read_text()
    rubric = Path(rubric_path).read_text()
    # The template ends with a placeholder marker; replace it with the rubric.
    if "[The full text of data/primitives.json v0.2 is concatenated" in template:
        # Naive insertion: append rubric at the placeholder boundary.
        body = template.split("# Rubric (v0.2)\n\n", 1)
        if len(body) == 2:
            return body[0] + "# Rubric (v0.2)\n\n" + rubric + "\n\nEnd of prompt. Return ONLY the JSON object specified above.\n"
    return template + "\n\n# Rubric (v0.2)\n\n" + rubric


def grade_judgment(
    judgment_text: str,
    *,
    model: str = DEFAULT_MODEL,
    temperature: float = DEFAULT_TEMPERATURE,
    prompt_template_path: Path = DEFAULT_PROMPT_PATH,
    max_tokens: int = 1024,
    extra_instruction: str | None = None,
    user_message_prefix: str = "Judgment text follows. Apply the v0.2 rubric and return strict JSON as specified.\n\n=== JUDGMENT ===\n",
) -> dict:
    """Single API call. Returns parsed JSON dict; raises on parse failure.
    `extra_instruction` is appended to the system prompt for perturbation runs."""
    client = _client()
    system = _build_system_prompt(prompt_template_path)
    if extra_instruction:
        system = system + "\n\n" + extra_instruction
    msg = client.messages.create(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user_message_prefix + judgment_text}],
    )
    text = "".join(b.text for b in msg.content if hasattr(b, "text"))
    # Extract first JSON object in the response.
    m = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not m:
        raise ValueError(f"No JSON in response. Raw:\n{text[:500]}")
    return json.loads(m.group(0))


def normalise_score(v):
    """Coerce score to int in {-1, 0, 1, 2}; otherwise None."""
    try:
        i = int(v)
        if i in (-1, 0, 1, 2):
            return i
    except (ValueError, TypeError):
        pass
    return None


def per_primitive(result: dict) -> dict:
    return {k: normalise_score(result.get(k)) for k in PRIM_KEYS + SP_KEYS}


def load_judgment_text(case_id: str, judgments_data: list, raw_root: Path) -> str | None:
    """Return raw text for a case. Looks under data/raw/<tribunal>/text/.
    Falls back to the entry's notes if no raw text available locally."""
    # Implementation depends on how raw text is laid out.
    # For now, callers pass text directly when they have it.
    return None


if __name__ == "__main__":
    print("Helper module — import grade_judgment from a runner script.")
    sys.exit(0)
