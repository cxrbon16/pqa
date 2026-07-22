"""Aşama 7 — Hugging Face'e yükleme (opsiyonel; `datasets` ve HF token gerekir)."""

import os

from .io_utils import read_jsonl


def run_publish(cfg, limit=None):
    from datasets import Dataset, DatasetDict  # geç import: sadece publish'te gerekli

    p = cfg.publish
    train = read_jsonl(os.path.join(cfg.data_dir, "train.jsonl"))
    test = read_jsonl(os.path.join(cfg.data_dir, "test.jsonl"))
    dd = DatasetDict(
        {
            "train": Dataset.from_list(train),
            "test": Dataset.from_list(test),
        }
    )
    dd.push_to_hub(p.repo_id, private=p.get("private", True))
    print(f"publish: train={len(train)} test={len(test)} -> hf.co/datasets/{p.repo_id}")
