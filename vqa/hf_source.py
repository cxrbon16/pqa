"""Aşama 1 (alternatif) — herhangi bir Hugging Face dataset'ini kaynak olarak kullanma.

Kolon adları koddan değil `config.yaml`'dan okunur (nokta ile nested alanlara erişim,
örn. "metadata.url"). Böylece kod değiştirmeden farklı bir HF dataset'ine geçilebilir:
sadece source.hf_dataset.* alanlarını yeni dataset'in kolon adlarına göre güncelle.
"""
import os

from tqdm import tqdm

from .io_utils import write_jsonl


def _get_path(row, path):
    """'metadata.url' gibi nokta ayraçlı alanlara eriş; yol geçersizse None döndür."""
    if not path:
        return None
    cur = row
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _derive_title(text, max_words=10, max_chars=80):
    """title_field verilmemişse metnin başından kısa bir sahte başlık türet."""
    first_line = text.split("\n", 1)[0].strip()
    if first_line.startswith("# "):  # wiki-dump türevi dataset'lerde yaygın "# Başlık" satırı
        return first_line[2:].strip()[:max_chars]
    head = " ".join(text.split()[:max_words])
    for sep in (", ", ". "):
        if sep in head:
            head = head.split(sep, 1)[0]
            break
    return head[:max_chars].strip()


def _strip_leading_heading(text):
    """'# Başlık\n...' formatında başlıyorsa başlık satırını gövdeden çıkar."""
    first_line, sep, rest = text.partition("\n")
    if sep and first_line.strip().startswith("# "):
        return rest.lstrip("\n")
    return text


def _passes_extra_filters(row, extra_filters):
    for f in extra_filters or []:
        val = _get_path(row, f["field"])
        if val is None:
            return False
        if "min" in f and val < f["min"]:
            return False
        if "max" in f and val > f["max"]:
            return False
    return True


def run_fetch_hf(cfg, limit=None):
    from datasets import load_dataset  # geç import: sadece bu kaynak seçiliyse gerekli

    h = cfg.source.hf_dataset
    n = limit or h.n_articles

    ds = load_dataset(h.repo_id, h.get("config_name"), split=h.get("split", "train"),
                      streaming=True)
    if h.get("shuffle", True):
        ds = ds.shuffle(seed=cfg.seed, buffer_size=h.get("shuffle_buffer", 10000))

    title_field = h.get("title_field")
    url_field = h.get("url_field")
    license_ = h.get("license", "unknown")
    source_name = h.get("source_name", h.repo_id)
    extra_filters = h.get("extra_filters")

    articles, seen = [], 0
    bar = tqdm(total=n, desc="fetch(hf)", unit="madde")
    for row in ds:
        if len(articles) >= n:
            break
        seen += 1
        text = _get_path(row, h.text_field)
        if not text or len(text.split()) < h.min_article_words:
            continue
        if not _passes_extra_filters(row, extra_filters):
            continue
        title = (_get_path(row, title_field) if title_field else None) or _derive_title(text)
        body = _strip_leading_heading(text)
        articles.append({
            "title": title,
            "url": (_get_path(row, url_field) or "") if url_field else "",
            "text": body,
            "source": source_name,
            "license": license_,
        })
        bar.update(1)
        bar.set_postfix(taranan=seen, son=title[:30])
    bar.close()

    out = os.path.join(cfg.data_dir, "01_articles.jsonl")
    write_jsonl(out, articles)
    print(f"fetch(hf): {len(articles)}/{seen} taranan kayıttan kabul edildi -> {out}")
    return articles
