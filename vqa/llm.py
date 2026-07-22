"""OpenAI-uyumlu chat endpoint istemcisi (vLLM, Ollama, OpenRouter, ...)."""
import json
import os
import re
import time

import requests


class ChatClient:
    def __init__(self, name, model, base_url, api_key_env=None,
                 temperature=0.0, max_tokens=512, timeout=120, retries=3):
        self.name = name
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.api_key = os.environ.get(api_key_env, "") if api_key_env else ""
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.retries = retries

    def chat(self, messages):
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        last_err = None
        for attempt in range(self.retries):
            try:
                r = requests.post(f"{self.base_url}/chat/completions",
                                  headers=headers, json=payload, timeout=self.timeout)
                if r.status_code in (429, 500, 502, 503):
                    raise RuntimeError(f"HTTP {r.status_code}: {r.text[:200]}")
                r.raise_for_status()
                return r.json()["choices"][0]["message"]["content"]
            except Exception as e:  # noqa: BLE001
                last_err = e
                time.sleep(2 ** attempt)
        raise RuntimeError(f"{self.name}: chat failed after {self.retries} tries: {last_err}")


def client_from_cfg(mcfg):
    return ChatClient(
        name=mcfg.get("name", mcfg["model"]),
        model=mcfg["model"],
        base_url=mcfg["base_url"],
        api_key_env=mcfg.get("api_key_env"),
        temperature=mcfg.get("temperature", 0.0),
        max_tokens=mcfg.get("max_tokens", 512),
        timeout=mcfg.get("timeout", 120),
        retries=mcfg.get("retries", 3),
    )


def extract_json(text):
    """Model çıktısındaki ilk JSON dizisini/objesini ayıkla."""
    text = re.sub(r"```(?:json)?", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    for open_c, close_c in (("[", "]"), ("{", "}")):
        start = text.find(open_c)
        end = text.rfind(close_c)
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                continue
    raise ValueError(f"JSON bulunamadı: {text[:200]!r}")
