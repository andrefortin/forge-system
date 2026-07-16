#!/usr/bin/env python3
"""
forge_llm.py — Standalone LLM client for all forges.
Zero dependencies on Pi, Story Forge, or any agent system.

Each forge copies this file into its scripts/ directory.
That's it. No shared utils. No cross-project imports.

Usage (in any forge):
    from forge_llm import call_llm
    data, err = call_llm(prompt, model="deepseek/deepseek-v4-flash")

Providers (tried in order):
    1. OpenRouter (OPENROUTER_API_KEY env var)
    2. DeepSeek Direct (DEEPSEEK_API_KEY env var) — fallback on rate limit

Config: ~/.config/forge_llm.json (optional override)
"""

import json, os, time, urllib.request, urllib.error
from datetime import datetime
from pathlib import Path

# ── Configuration ───────────────────────────────────────────────

CONFIG_FILE = os.path.expanduser("~/.config/forge_llm.json")

DEFAULT_CONFIG = {
    "openrouter_url": "https://openrouter.ai/api/v1/chat/completions",
    "deepseek_url": "https://api.deepseek.com/v1/chat/completions",
    "default_model": "deepseek/deepseek-v4-flash",
    "max_tokens": 6000,
    "temperature": 0.8,
    "max_retries": 3,
    "retry_delay": 2,
    "timeout": 120,
}


def _load_config():
    config = dict(DEFAULT_CONFIG)
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE) as f:
                config.update(json.load(f))
        except: pass
    return config


def _api_keys():
    """Get API keys from environment."""
    return {
        "openrouter": os.environ.get("OPENROUTER_API_KEY", ""),
        "deepseek": os.environ.get("DEEPSEEK_API_KEY", ""),
    }


def call_llm(prompt: str, system_prompt: str = None, model: str = None,
             temperature: float = None, max_tokens: int = None, timeout: int = None):
    """Call LLM via OpenRouter (primary) or DeepSeek Direct (fallback).
    
    Returns: (data_dict, None) on success, (None, error_string) on failure.
    """
    config = _load_config()
    keys = _api_keys()
    
    model = model or config["default_model"]
    temp = temperature if temperature is not None else config["temperature"]
    max_tok = max_tokens or config["max_tokens"]
    timeout_s = timeout or config["timeout"]
    
    body = {
        "model": model,
        "messages": [],
        "temperature": temp,
        "max_tokens": max_tok,
    }
    
    if system_prompt:
        body["messages"].append({"role": "system", "content": system_prompt})
    body["messages"].append({"role": "user", "content": prompt})
    
    payload = json.dumps(body).encode("utf-8")
    
    # Try OpenRouter first
    or_key = keys.get("openrouter", "")
    if or_key:
        data, err = _try_provider(config["openrouter_url"], or_key, payload, timeout_s)
        if not err:
            return data, None
        # Rate limited or failed — fall through to DeepSeek Direct
    
    # Try DeepSeek Direct as fallback
    ds_key = keys.get("deepseek", "")
    if ds_key:
        # Strip provider prefix for direct API (deepseek/deepseek-v4-flash → deepseek-v4-flash)
        direct_model = model.split("/")[-1] if "/" in model else model
        direct_body = dict(body)
        direct_body["model"] = direct_model
        direct_payload = json.dumps(direct_body).encode("utf-8")
        
        data, err = _try_provider(config["deepseek_url"], ds_key, direct_payload, timeout_s)
        if not err:
            return data, None
    
    return None, "No API keys configured. Set OPENROUTER_API_KEY or DEEPSEEK_API_KEY."


def _try_provider(url: str, api_key: str, payload: bytes, timeout: int):
    """Try a single provider. Returns (data, error)."""
    for attempt in range(DEFAULT_CONFIG["max_retries"]):
        try:
            req = urllib.request.Request(url, data=payload)
            req.add_header("Content-Type", "application/json")
            req.add_header("Authorization", f"Bearer {api_key}")
            
            resp = urllib.request.urlopen(req, timeout=timeout)
            raw = json.loads(resp.read().decode("utf-8"))
            
            # Extract content from response
            choices = raw.get("choices", [])
            if choices:
                msg = choices[0].get("message", {})
                content = msg.get("content", "")
                if content:
                    return content, None
            
            return None, f"Empty response: {json.dumps(raw)[:200]}"
            
        except urllib.error.HTTPError as e:
            status = e.code
            if status == 429:  # Rate limited
                delay = DEFAULT_CONFIG["retry_delay"] * (2 ** attempt)
                time.sleep(delay)
                continue
            return None, f"HTTP {status}: {e.read().decode()[:200]}"
            
        except Exception as e:
            if attempt < DEFAULT_CONFIG["max_retries"] - 1:
                time.sleep(DEFAULT_CONFIG["retry_delay"])
                continue
            return None, str(e)[:200]
    
    return None, "Max retries exceeded"


# ── Quick test ───────────────────────────────────────────────────

if __name__ == "__main__":
    print("Testing forge_llm...")
    result, err = call_llm(
        "Say 'forge_llm is working' in one sentence.",
        system_prompt="Be concise.",
        max_tokens=50,
    )
    if err:
        print(f"❌ {err}")
    else:
        print(f"✅ {result[:100]}")
