"""
LLM client — unified wrapper over OpenAI SDK and Anthropic SDK.

Routing logic:
  • If OPENAI_API_KEY is set → use openai.OpenAI (compatible with Kimi, DeepSeek …)
  • Otherwise              → use anthropic.Anthropic (Claude, MiniMax, GLM …)
"""

from __future__ import annotations

import json
import time
from typing import Any

from src import config
from src import logger

log = logger.get("llm.client")

# ── Lazy SDK imports ────────────────────────────────────────────────────────

_openai_client = None
_anthropic_client = None


def _get_openai():
    global _openai_client
    if _openai_client is None:
        import openai
        kwargs: dict[str, Any] = {"api_key": config.OPENAI_API_KEY}
        if config.OPENAI_BASE_URL:
            kwargs["base_url"] = config.OPENAI_BASE_URL
        _openai_client = openai.OpenAI(**kwargs)
        log.info("OpenAI SDK client initialised (base_url=%s)", config.OPENAI_BASE_URL or "default")
    return _openai_client


def _get_anthropic():
    global _anthropic_client
    if _anthropic_client is None:
        import anthropic
        kwargs: dict[str, Any] = {"api_key": config.ANTHROPIC_API_KEY}
        if config.ANTHROPIC_BASE_URL:
            kwargs["base_url"] = config.ANTHROPIC_BASE_URL
        _anthropic_client = anthropic.Anthropic(**kwargs)
        log.info("Anthropic SDK client initialised (base_url=%s)", config.ANTHROPIC_BASE_URL or "default")
    return _anthropic_client


# ── Public API ──────────────────────────────────────────────────────────────

def chat(
    system: str,
    user: str,
    *,
    max_tokens: int | None = None,
    temperature: float | None = None,
) -> str:
    """
    Send a single-turn chat completion and return the assistant text.

    Parameters are resolved in order:
      1. Explicit argument
      2. LLM_TEMPERATURE / LLM_MAX_TOKENS from config
      3. Hard-coded default (temperature=0.2, max_tokens=LLM_MAX_TOKENS)
    """
    max_tokens = max_tokens or config.LLM_MAX_TOKENS
    temperature = temperature if temperature is not None else (
        config.LLM_TEMPERATURE if config.LLM_TEMPERATURE is not None else 0.2
    )

    t0 = time.time()

    if config.USE_OPENAI_SDK:
        text = _chat_openai(system, user, max_tokens=max_tokens, temperature=temperature)
    else:
        text = _chat_anthropic(system, user, max_tokens=max_tokens, temperature=temperature)

    elapsed = int((time.time() - t0) * 1000)
    log.debug("LLM responded in %d ms (%d chars)", elapsed, len(text))
    return text


def chat_json(
    system: str,
    user: str,
    *,
    max_tokens: int | None = None,
    temperature: float | None = None,
) -> Any:
    """
    Like chat() but parse the response as JSON.
    Strips markdown code fences if present.
    """
    raw = chat(system, user, max_tokens=max_tokens, temperature=temperature)
    return _parse_json(raw)


# ── OpenAI SDK path ─────────────────────────────────────────────────────────

def _chat_openai(system: str, user: str, *, max_tokens: int, temperature: float) -> str:
    client = _get_openai()
    log.debug("→ OpenAI request  model=%s  max_tokens=%d  temperature=%.2f",
              config.MODEL_ID, max_tokens, temperature)
    log.debug("  system[%d chars]  user[%d chars]", len(system), len(user))

    resp = client.chat.completions.create(
        model=config.MODEL_ID,
        max_tokens=max_tokens,
        temperature=temperature,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    text = resp.choices[0].message.content or ""
    log.debug("← OpenAI response  %d chars  finish=%s",
              len(text), resp.choices[0].finish_reason)
    return text


# ── Anthropic SDK path ──────────────────────────────────────────────────────

def _chat_anthropic(system: str, user: str, *, max_tokens: int, temperature: float) -> str:
    client = _get_anthropic()
    log.debug("→ Anthropic request  model=%s  max_tokens=%d  temperature=%.2f",
              config.MODEL_ID, max_tokens, temperature)
    log.debug("  system[%d chars]  user[%d chars]", len(system), len(user))

    resp = client.messages.create(
        model=config.MODEL_ID,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    text = resp.content[0].text if resp.content else ""
    log.debug("← Anthropic response  %d chars  stop=%s",
              len(text), resp.stop_reason)
    return text


# ── Helpers ─────────────────────────────────────────────────────────────────

def chat_multi(
    system: str,
    messages: list[dict[str, str]],
    *,
    max_tokens: int | None = None,
    temperature: float | None = None,
) -> str:
    """
    Multi-turn chat completion.  `messages` is a list of
    {"role": "user"|"assistant", "content": "..."}.
    """
    max_tokens = max_tokens or config.LLM_MAX_TOKENS
    temperature = temperature if temperature is not None else (
        config.LLM_TEMPERATURE if config.LLM_TEMPERATURE is not None else 0.2
    )

    t0 = time.time()

    if config.USE_OPENAI_SDK:
        text = _chat_multi_openai(system, messages, max_tokens=max_tokens, temperature=temperature)
    else:
        text = _chat_multi_anthropic(system, messages, max_tokens=max_tokens, temperature=temperature)

    elapsed = int((time.time() - t0) * 1000)
    log.debug("LLM multi-turn responded in %d ms (%d chars)", elapsed, len(text))
    return text


def _chat_multi_openai(system: str, messages: list[dict[str, str]], *,
                       max_tokens: int, temperature: float) -> str:
    client = _get_openai()
    full_messages = [{"role": "system", "content": system}] + messages
    log.debug("→ OpenAI multi-turn  model=%s  turns=%d", config.MODEL_ID, len(messages))
    resp = client.chat.completions.create(
        model=config.MODEL_ID,
        max_tokens=max_tokens,
        temperature=temperature,
        messages=full_messages,
    )
    return resp.choices[0].message.content or ""


def _chat_multi_anthropic(system: str, messages: list[dict[str, str]], *,
                          max_tokens: int, temperature: float) -> str:
    client = _get_anthropic()
    log.debug("→ Anthropic multi-turn  model=%s  turns=%d", config.MODEL_ID, len(messages))
    resp = client.messages.create(
        model=config.MODEL_ID,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system,
        messages=messages,
    )
    return resp.content[0].text if resp.content else ""


def _parse_json(raw: str) -> Any:
    """Extract JSON from an LLM response, tolerating markdown code fences and thinking tags."""
    import re
    text = raw.strip()

    # Strip <think>...</think> blocks (some models emit internal reasoning)
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

    # Strip ```json ... ``` fences
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)

    # First try strict parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Repair common LLM JSON mistakes:
    # 1. Remove trailing commas before } or ]
    repaired = re.sub(r",\s*([}\]])", r"\1", text)
    # 2. Remove JS-style comments
    repaired = re.sub(r"//[^\n]*", "", repaired)
    # 3. Fix unquoted keys (simple cases)
    repaired = re.sub(r"(?<=[\{,])\s*(\w+)\s*:", r' "\1":', repaired)

    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        pass

    # Last resort: extract first { ... } or [ ... ] block
    for opener, closer in [("{", "}"), ("[", "]")]:
        start = text.find(opener)
        if start == -1:
            continue
        depth = 0
        for i in range(start, len(text)):
            if text[i] == opener:
                depth += 1
            elif text[i] == closer:
                depth -= 1
                if depth == 0:
                    candidate = text[start : i + 1]
                    candidate = re.sub(r",\s*([}\]])", r"\1", candidate)
                    try:
                        return json.loads(candidate)
                    except json.JSONDecodeError:
                        break

    # Give up — raise with original text for debugging
    return json.loads(text)
