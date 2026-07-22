"""Aşama 3 — pasajlardan soru üretimi (generator model)."""
import os

from .io_utils import read_jsonl, write_jsonl
from .llm import client_from_cfg, extract_json
from .normalize import contains_span

GEN_PROMPT = """Aşağıdaki metinden {n} adet kısa cevaplı soru üret.

Kurallar:
- Cevap, metinde BİREBİR geçen kısa bir ifade olmalı (en fazla {max_ans} kelime: isim, tarih, sayı, terim).
- Soru yalnızca bu metin okunarak cevaplanabilmeli.
- Evet/hayır sorusu, muğlak soru ve "yukarıdaki" gibi konum referansı yasak.
- "cevap_alternatifleri" alanına cevabın kabul edilebilir farklı yazımlarını koy (yoksa boş liste).
- Yalnızca geçerli JSON döndür, başka hiçbir şey yazma:
[{{"soru": "...", "cevap": "...", "cevap_alternatifleri": ["..."]}}]

METİN:
{passage}"""


def run_generate(cfg, limit=None):
    g = cfg.generation
    client = client_from_cfg(g.model)
    passages = read_jsonl(os.path.join(cfg.data_dir, "02_passages.jsonl"))
    if limit:
        passages = passages[:limit]

    records, failed = [], 0
    for i, p in enumerate(passages):
        prompt = GEN_PROMPT.format(n=g.questions_per_passage,
                                   max_ans=cfg.filters.max_answer_words,
                                   passage=p["passage"])
        try:
            raw = client.chat([{"role": "user", "content": prompt}])
            items = extract_json(raw)
        except Exception as e:  # noqa: BLE001
            print(f"  ! {p['passage_id']}: üretim hatası: {e}")
            failed += 1
            continue
        if isinstance(items, dict):
            items = [items]
        for qi, item in enumerate(items[:g.questions_per_passage], start=1):
            q, a = item.get("soru", "").strip(), str(item.get("cevap", "")).strip()
            if not q or not a:
                continue
            records.append({
                "id": f"{p['passage_id']}-q{qi}",
                **{k: p[k] for k in ("passage_id", "article_title", "section",
                                     "passage", "source", "source_url", "license")},
                "question": q,
                "answer": a,
                "answer_aliases": [str(x).strip() for x in item.get("cevap_alternatifleri", []) if str(x).strip()],
                "answer_in_passage": contains_span(p["passage"], a),
                "generator_model": client.model,
            })
        if (i + 1) % 10 == 0:
            print(f"  generate: {i + 1}/{len(passages)} pasaj işlendi")

    out = os.path.join(cfg.data_dir, "03_candidates.jsonl")
    write_jsonl(out, records)
    print(f"generate: {len(records)} soru adayı ({failed} pasaj hatalı) -> {out}")
    return records
