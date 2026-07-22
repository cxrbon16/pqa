"""Aşama 1 — TR Wikipedia'dan madde metni çekme (MediaWiki API)."""
import os
import time
import urllib.parse

import requests

from .io_utils import write_jsonl

UA = {"User-Agent": "verifiable-qa-pipeline/0.1 (research pilot)"}


def _api_get(api_url, params, retries=5):
    params = {"format": "json", "formatversion": "2", **params}
    for attempt in range(retries):
        r = requests.get(api_url, params=params, headers=UA, timeout=30)
        if r.status_code == 429 or r.status_code >= 500:
            wait = int(r.headers.get("Retry-After", 0)) or 2 ** attempt
            time.sleep(min(wait, 60))
            continue
        r.raise_for_status()
        return r.json()
    r.raise_for_status()
    return r.json()


def fetch_random_titles(api_url, n):
    titles = []
    while len(titles) < n:
        batch = min(500, n - len(titles))
        data = _api_get(api_url, {"action": "query", "list": "random",
                                  "rnnamespace": 0, "rnlimit": batch})
        titles += [p["title"] for p in data["query"]["random"]]
        time.sleep(0.2)
    return titles[:n]


def fetch_category_titles(api_url, category, n):
    titles, cont = [], {}
    while len(titles) < n:
        data = _api_get(api_url, {"action": "query", "list": "categorymembers",
                                  "cmtitle": f"Kategori:{category}", "cmnamespace": 0,
                                  "cmlimit": min(500, n - len(titles)), **cont})
        titles += [p["title"] for p in data["query"]["categorymembers"]]
        if "continue" not in data:
            break
        cont = data["continue"]
        time.sleep(0.2)
    return titles[:n]


def fetch_extract(api_url, title):
    data = _api_get(api_url, {"action": "query", "prop": "extracts",
                              "explaintext": 1, "redirects": 1, "titles": title})
    pages = data["query"]["pages"]
    if not pages or "extract" not in pages[0]:
        return None
    site = api_url.split("/w/")[0]
    return {
        "title": pages[0]["title"],
        "url": f"{site}/wiki/{urllib.parse.quote(pages[0]['title'].replace(' ', '_'))}",
        "text": pages[0]["extract"],
    }


def run_fetch(cfg, limit=None):
    w = cfg.source.wikipedia_api
    n = limit or w.n_articles
    if w.mode == "category" and w.get("category"):
        titles = fetch_category_titles(w.api_url, w.category, n)
    elif w.mode == "titles" and w.get("titles_file"):
        with open(w.titles_file, encoding="utf-8") as f:
            titles = [t.strip() for t in f if t.strip()][:n]
    else:
        titles = fetch_random_titles(w.api_url, n)

    articles = []
    for i, title in enumerate(titles):
        art = fetch_extract(w.api_url, title)
        time.sleep(0.5)
        if art is None or len(art["text"].split()) < w.min_article_words:
            continue
        art["source"] = "tr.wikipedia"
        art["license"] = "CC BY-SA 4.0"
        articles.append(art)
        print(f"  [{i + 1}/{len(titles)}] {art['title']} ({len(art['text'].split())} kelime)")

    out = os.path.join(cfg.data_dir, "01_articles.jsonl")
    write_jsonl(out, articles)
    print(f"fetch: {len(articles)}/{len(titles)} madde -> {out}")
    return articles
