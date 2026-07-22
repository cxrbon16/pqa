"""Aşama 5 — çözücü model grubu: her soruyu pasajla birlikte N modele çözdür."""
import os
import re
from concurrent.futures import ThreadPoolExecutor

from .io_utils import read_jsonl, write_jsonl
from .llm import client_from_cfg
from .normalize import is_match

SOLVE_PROMPT = """Aşağıdaki metni oku ve soruyu metne dayanarak cevapla.
Yalnızca kısa cevabı yaz (en fazla birkaç kelime). Açıklama yazma.

METİN:
{passage}

SORU: {question}
CEVAP:"""


def _parse_answer(raw):
    lines = [l.strip() for l in raw.strip().split("\n") if l.strip()]
    ans = lines[-1] if lines else ""
    return re.sub(r"^cevap\s*:\s*", "", ans, flags=re.IGNORECASE).strip()


def _solve_one(client, rec):
    prompt = SOLVE_PROMPT.format(passage=rec["passage"], question=rec["question"])
    try:
        raw = client.chat([{"role": "user", "content": prompt}])
        ans = _parse_answer(raw)
        ok = is_match(rec["answer"], rec.get("answer_aliases"), ans)
    except Exception as e:  # noqa: BLE001
        ans, ok = f"__error__: {e}", False
    return client.name, ans, ok


def run_solve(cfg, limit=None):
    s = cfg.solving
    clients = [client_from_cfg(m) for m in s.solvers]
    records = read_jsonl(os.path.join(cfg.data_dir, "04_filtered.jsonl"))
    if limit:
        records = records[:limit]

    if not clients:
        print("solve: solving.solvers boş — doğrulama devre dışı, kayıtlar işaretlenmeden geçiyor")
        for rec in records:
            rec["solver_answers"] = {}
            rec["solver_results"] = {}
            rec["solve_count"] = 0
            rec["solve_rate"] = None
    else:
        with ThreadPoolExecutor(max_workers=s.max_workers) as ex:
            for i, rec in enumerate(records):
                results = list(ex.map(lambda c: _solve_one(c, rec), clients))
                rec["solver_answers"] = {name: ans for name, ans, _ in results}
                rec["solver_results"] = {name: ok for name, _, ok in results}
                rec["solve_count"] = sum(ok for _, _, ok in results)
                rec["solve_rate"] = round(rec["solve_count"] / len(clients), 3)
                if (i + 1) % 10 == 0:
                    print(f"  solve: {i + 1}/{len(records)} soru çözüldü")

    out = os.path.join(cfg.data_dir, "05_solved.jsonl")
    write_jsonl(out, records)
    print(f"solve: {len(records)} soru x {len(clients)} çözücü -> {out}")
    return records
