"""
Shared text-processing helpers for the pipeline.
"""

from __future__ import annotations


def strip_fences(text: str) -> str:
    """Remove markdown code fences if the LLM wrapped the output."""
    text = text.strip()
    # Strip opening fence (```js / ```javascript / ```)
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]  # drop ```{lang} line
        text = "\n".join(lines).strip()
    # Strip trailing fence — handle ``` possibly followed by whitespace
    if text.rstrip().endswith("```"):
        text = text.rstrip()[:-3].rstrip()
    # Also strip any ``` that appears alone on the last non-empty line
    lines = text.split("\n")
    while lines and lines[-1].strip() in ("", "```"):
        if lines[-1].strip() == "```":
            lines.pop()
        elif lines[-1].strip() == "":
            lines.pop()
        else:
            break
    text = "\n".join(lines)
    return text
