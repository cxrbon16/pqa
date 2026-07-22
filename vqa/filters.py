"""Aşama 4 — çözücülerden önce ucuz otomatik filtreler: format, span, dedup."""
import os
from collections import Counter

from .io_utils import read_jsonl, write_jsonl
from .normalize import norm

FORBIDDEN = ("yukarıdaki", "yukarıda", "bu pasaj", "pasajda", "paragrafta")


def _jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _check(rec, f):
    q, a = rec["question"], rec["answer"]
    if not rec.get("answer_in_passage"):
        return "span"
    if len(a.split()) > f.max_answer_words:
        return "cevap_uzun"
    if q.count("?") != 1 or not q.endswith("?"):
        return "format_soru"
    if not 4 <= len(q.split()) <= 40:
        return "soru_uzunluk"
    nq = norm(q)
    if any(w in nq for w in FORBIDDEN):
        return "konum_referansı"
    if norm(a) in nq:
        return "cevap_soruda"
    return None


def run_filters(cfg, limit=None):
    f = cfg.filters
    records = read_jsonl(os.path.join(cfg.data_dir, "03_candidates.jsonl"))
    if limit:
        records = records[:limit]

    # dedup: dataset genelinde birebir tekrar + aynı pasaj içinde benzerlik eşiği
    kept, rejects = [], Counter()
    seen_exact, passage_tokens = set(), {}
    for rec in records:
        reason = _check(rec, f)
        if reason is None:
            key = (norm(rec["question"]), norm(rec["answer"]))
            toks = set(key[0].split())
            siblings = passage_tokens.setdefault(rec["passage_id"], [])
            if key in seen_exact:
                reason = "duplicate"
            elif any(_jaccard(toks, prev) >= f.dedup_jaccard for prev in siblings):
                reason = "duplicate_pasaj_içi"
            else:
                seen_exact.add(key)
                siblings.append(toks)
        if reason:
            rejects[reason] += 1
        else:
            kept.append(rec)

    out = os.path.join(cfg.data_dir, "04_filtered.jsonl")
    write_jsonl(out, kept)
    print(f"filter: {len(kept)}/{len(records)} kaldı -> {out}")
    for reason, n in rejects.most_common():
        print(f"  elendi[{reason}]: {n}")
    return kept
