# Türkçe Verifiable QA Pipeline

Tasarım için bkz. [ENTRY.md](ENTRY.md). Modüler yapı: her aşama ayrı modül, her aşamanın
çıktısı `data/` altında ayrı JSONL — istediğin aşamadan yeniden başlayabilirsin.

## Kurulum

```bash
pip install -r requirements.txt
```

## Kullanım

```bash
python -m vqa all                      # tüm pipeline (fetch -> band)
python -m vqa fetch --limit 20         # tek aşama, ilk 20 kayıtla
python -m vqa solve                    # 04_filtered.jsonl'den devam et
python -m vqa publish                  # data/train.jsonl + test.jsonl -> HF repo
```

Aşamalar ve çıktıları:

| Aşama | Modül | Çıktı |
|---|---|---|
| fetch | `vqa/fetch.py` (dispatcher) → `vqa/hf_source.py` \| `vqa/wiki.py` | `data/01_articles.jsonl` |
| passages | `vqa/passages.py` | `data/02_passages.jsonl` |
| generate | `vqa/generate.py` | `data/03_candidates.jsonl` |
| filter | `vqa/filters.py` | `data/04_filtered.jsonl` |
| solve | `vqa/solve.py` | `data/05_solved.jsonl` |
| band | `vqa/band.py` | `data/06_final.jsonl` + `train.jsonl` / `test.jsonl` |
| publish | `vqa/publish.py` | HF dataset repo |

## Kaynak değiştirme (fetch aşaması)

`fetch` aşaması iki moddan birini kullanır (`config.yaml` → `source.type`):

- **`hf_dataset`** (varsayılan): herhangi bir Hugging Face dataset'i, `datasets.load_dataset(..., streaming=True)`
  ile. Kolon adları koddan değil `source.hf_dataset.*` alanlarından okunur — nested alanlara nokta ile erişilir
  (örn. `metadata.url`). Başka bir dataset'e geçmek için **kod değişmez**, sadece bu blok güncellenir:

  ```yaml
  source:
    type: hf_dataset
    hf_dataset:
      repo_id: BILGEM-AI/BILGE-Wiki-Tr-Plus
      config_name: default
      split: train
      text_field: text              # ana metin kolonu
      title_field: null              # yoksa metnin başından otomatik türetilir
      url_field: metadata.url        # nested alan örneği
      license: "CC BY-SA 4.0"
      n_articles: 100
      min_article_words: 300
      extra_filters:                 # opsiyonel eşik filtreleri (nested alan da olabilir)
        - field: metadata.quality_score
          min: 3.0
  ```

  `config.yaml` içinde `wikimedia/wikipedia` (config: `20231101.tr`) için hazır bir örnek bloğu da (yorum
  satırı olarak) mevcuttur.

- **`wikipedia_api`**: doğrudan MediaWiki API'sinden canlı çekim (`source.wikipedia_api.*`). Rate-limit'e
  tabidir (429'a karşı `Retry-After` destekli backoff var), `hf_dataset`'e göre daha yavaştır.

## Colab'da çalıştırma

Adım adım, çalıştırılabilir hücrelerle hazır bir defter: **[colab_pipeline.ipynb](colab_pipeline.ipynb)**
([Colab'da aç](https://colab.research.google.com/github/cxrbon16/pqa/blob/main/colab_pipeline.ipynb)).
Kapsadıkları: GPU kontrolü, repo klonlama, Ollama kurulup üretici + çözücü modellerin indirilmesi,
`--limit` ile duman testi, Drive'a bağlanıp `data_dir`'i taşıyarak oturum kopmalarına dayanıklı hale
getirme, tam çalıştırma ve HF'e yayınlama.

Tüm modeller OpenAI-uyumlu endpoint üzerinden çağrılır (`vqa/llm.py`) — Ollama, vLLM ve
OpenRouter'ın üçü de bu arayüzü sunar; `config.yaml`'da `base_url` + `model` değiştirmek yeter.
Hosted endpoint (örn. OpenRouter) için config'de `api_key_env: OPENROUTER_API_KEY` yaz ve
ortam değişkenini ayarla.
