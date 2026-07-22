"""Aşama 6 — bant filtresi, gold şüphe kontrolü, zorluk etiketi, train/test split."""
import datetime
import os
import random
from collections import Counter

from .io_utils import read_jsonl, write_jsonl
from .normalize import is_match

FINAL_FIELDS = ("id", "passage", "question", "answer", "answer_aliases",
                "source", "source_url", "license", "difficulty",
                "solver_results", "solve_rate", "generator_model", "created_at")


def _gold_suspect(rec):
    """Çözücülerin çoğunluğu kendi arasında tutarlı ama gold'dan farklıysa gold şüpheli."""
    answers = [a for a in rec["solver_answers"].values() if not a.startswith("__error__")]
    n = len(rec["solver_answers"])
    for ans in answers:
        agree = sum(1 for other in answers if is_match(ans, [], other))
        if agree > n / 2 and not is_match(rec["answer"], rec.get("answer_aliases"), ans):
            return True
    return False


def _difficulty(rate, b):
    if rate <= b.hard_max_rate:
        return "hard"
    if rate <= b.medium_max_rate:
        return "medium"
    return "easy"


def run_band(cfg, limit=None):
    b = cfg.banding
    records = read_jsonl(os.path.join(cfg.data_dir, "05_solved.jsonl"))
    if limit:
        records = records[:limit]

    today = datetime.date.today().isoformat()
    kept, rejects = [], Counter()
    for rec in records:
        n_solvers = len(rec["solver_results"])
        if rec["solve_count"] < b.min_solved:
            rejects["gold_şüpheli" if _gold_suspect(rec) else "çözülemez"] += 1
            continue
        if b.drop_trivial and rec["solve_count"] == n_solvers:
            rejects["çok_kolay"] += 1
            continue
        rec["difficulty"] = _difficulty(rec["solve_rate"], b)
        rec["created_at"] = today
        kept.append({k: rec.get(k) for k in FINAL_FIELDS})

    write_jsonl(os.path.join(cfg.data_dir, "06_final.jsonl"), kept)
    print(f"band: {len(kept)}/{len(records)} kaldı")
    for reason, n in rejects.most_common():
        print(f"  elendi[{reason}]: {n}")
    for d, n in Counter(r["difficulty"] for r in kept).most_common():
        print(f"  zorluk[{d}]: {n}")

    rng = random.Random(cfg.seed)
    shuffled = kept[:]
    rng.shuffle(shuffled)
    n_test = int(len(shuffled) * b.test_fraction)
    test, train = shuffled[:n_test], shuffled[n_test:]
    write_jsonl(os.path.join(cfg.data_dir, "train.jsonl"), train)
    write_jsonl(os.path.join(cfg.data_dir, "test.jsonl"), test)
    print(f"split: train={len(train)} test={len(test)} (test elle incelenmeli!)")
    return kept
