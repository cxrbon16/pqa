"""Aşama 2 — madde metninden 200-500 kelimelik pasajlar çıkarma."""
import os
import re

from .io_utils import read_jsonl, write_jsonl
from .normalize import tr_lower

SKIP_SECTIONS = {
    "kaynakça", "kaynaklar", "dış bağlantılar", "ayrıca bakınız", "notlar",
    "dipnotlar", "galeri", "filmografi", "diskografi", "bibliyografya",
    "eserleri", "ödülleri", "istatistikler", "başarıları",
}

_SECTION_RE = re.compile(r"^==+\s*(.+?)\s*==+\s*$", re.MULTILINE)


def split_sections(text):
    """explaintext çıktısını (başlık, gövde) çiftlerine böl; giriş bölümü dahil."""
    sections, last_end, last_title = [], 0, "__lead__"
    for m in _SECTION_RE.finditer(text):
        body = text[last_end:m.start()].strip()
        if body:
            sections.append((last_title, body))
        last_title, last_end = m.group(1), m.end()
    body = text[last_end:].strip()
    if body:
        sections.append((last_title, body))
    return sections


def _looks_like_list(body):
    lines = [l for l in body.split("\n") if l.strip()]
    if len(lines) < 3:
        return False
    short = sum(1 for l in lines if len(l.split()) < 6)
    return short / len(lines) > 0.5


def _chunks(body, min_words, max_words):
    """Paragrafları min-max kelime aralığında pasajlara topla."""
    paras = [p.strip() for p in body.split("\n") if p.strip()]
    out, cur, cur_words = [], [], 0
    for p in paras:
        w = len(p.split())
        if cur_words + w > max_words and cur_words >= min_words:
            out.append("\n".join(cur))
            cur, cur_words = [], 0
        cur.append(p)
        cur_words += w
    if cur and min_words <= cur_words <= max_words:
        out.append("\n".join(cur))
    return out


def run_passages(cfg, limit=None):
    p = cfg.passages
    articles = read_jsonl(os.path.join(cfg.data_dir, "01_articles.jsonl"))
    if limit:
        articles = articles[:limit]

    records, pid = [], 0
    for art in articles:
        count = 0
        for title, body in split_sections(art["text"]):
            if tr_lower(title) in SKIP_SECTIONS or _looks_like_list(body):
                continue
            for chunk in _chunks(body, p.min_words, p.max_words):
                if count >= p.max_passages_per_article:
                    break
                pid += 1
                count += 1
                records.append({
                    "passage_id": f"trwiki-{pid:06d}",
                    "article_title": art["title"],
                    "section": title,
                    "passage": chunk,
                    "source": art["source"],
                    "source_url": art["url"],
                    "license": art["license"],
                })

    out = os.path.join(cfg.data_dir, "02_passages.jsonl")
    write_jsonl(out, records)
    print(f"passages: {len(articles)} maddeden {len(records)} pasaj -> {out}")
    return records
