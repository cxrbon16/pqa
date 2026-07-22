"""Aşama 1 dispatcher — `source.type`'a göre doğru fetch implementasyonunu çalıştırır."""
from .hf_source import run_fetch_hf
from .wiki import run_fetch as run_fetch_wikipedia_api

FETCHERS = {
    "wikipedia_api": run_fetch_wikipedia_api,
    "hf_dataset": run_fetch_hf,
}


def run_fetch(cfg, limit=None):
    source_type = cfg.source.get("type", "wikipedia_api")
    if source_type not in FETCHERS:
        raise ValueError(f"Bilinmeyen source.type: {source_type!r} (seçenekler: {list(FETCHERS)})")
    return FETCHERS[source_type](cfg, limit=limit)
