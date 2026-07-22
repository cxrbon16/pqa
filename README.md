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

## Colab: GPU sunucusu + tünel, pipeline dışarıda

`colab_pipeline.ipynb` ([Colab'da aç](https://colab.research.google.com/github/cxrbon16/pqa/blob/main/colab_pipeline.ipynb))
artık pipeline'ın kendisini çalıştırmıyor — tek işi **Ollama**'yı GPU ile ayağa kaldırıp
[Cloudflare Quick Tunnel](https://github.com/cloudflare/cloudflared) ile dışarıya açmak (hesap
gerektirmez). Adımları: GPU kontrolü, Ollama kurulumu, üretici modelin (`gemma4:31b-it-bf16`)
indirilmesi, GPU'da çalıştığının doğrulanması, tünel açılıp `https://xxxx.trycloudflare.com`
URL'sinin yazdırılması. (vLLM denendi ama nightly build'in CUDA sürüm uyumsuzlukları — bkz. git
geçmişi — çözülemedi; Ollama'ya geri dönüldü. Gemma 4'ün thinking çıktısının `content`'i boş/yarım
bırakması sorunu `max_tokens`'ı 800'den 2000'e çıkararak hafifletildi.)

Pipeline (`fetch/passages/generate/filter/solve/band/publish`) bu repoyu klonlayan **herhangi bir
makineden** çalışır; sadece `config.yaml` → `generation.model.base_url` (ve varsa `solving.solvers[].base_url`)
alanlarını tünel URL'sine (`https://xxxx.trycloudflare.com/v1`) çevir. Tüm modeller OpenAI-uyumlu
endpoint üzerinden çağrılır (`vqa/llm.py`) — Ollama, vLLM ve OpenRouter'ın üçü de bu arayüzü sunar.

Colab sekmesi açık kalmalı: hem `ollama serve` hem `cloudflared` o çalışma zamanı sonlanınca ölür.
