# Türkçe Verifiable QA Dataset — Entry Doc

## Amaç
Türkçe kaynak metinlerden (Wikipedia + kamu metinleri + haber + eğitim içeriği) otomatik üretilmiş,
**model konsensüsü ile çözülebilirliği doğrulanmış**, kısa cevaplı (exact-match) okuduğunu anlama (RC)
soruları içeren bir dataset. Çift kullanım: büyük **train split** (RLVR/GRPO tarzı eğitim) +
küçük, temiz **test split** (benchmark).

Pilot hedefi: **~1.000 soru** (≈ 600–1.000 pasaj).

## Pipeline

```
[1] Kaynak toplama ──> [2] Pasaj çıkarma ──> [3] Soru üretimi ──> [4] Otomatik filtreler
        │                                                              │
        └── TR Wikipedia, Vikikaynak,                                  v
            haber arşivi, ders kitabı                          [5] Çözücü grubu (N model)
                                                                       │
                                                                       v
                                                              [6] Bant filtresi + zorluk etiketi
                                                                       │
                                                                       v
                                                              [7] JSONL → HF dataset repo
```

### 1. Kaynak toplama
- **TR Wikipedia** (öncelik): API ile madde çekimi; seçkin/kaliteli madde listelerinden başla. Lisans: CC BY-SA.
- **Vikikaynak / kamu metinleri**: telifsiz edebi ve resmî metinler (çeşitlilik).
- **Haber arşivleri**: yalnızca lisansı uygun kaynaklar; kontaminasyon riski nedeniyle düşük pay.
- **Ders kitabı / eğitim içeriği**: MEB açık kaynakları vb.; lisans tek tek kontrol edilir.
- Her kayıtta `source`, `source_url`, `license` alanları zorunlu.

### 2. Pasaj çıkarma
- **200–500 kelime**lik kendi içinde anlamlı bölümler (başlık bazlı bölme + uzunluk filtresi).
- Elenenler: tablo/listeye dayalı bölümler, dış bağlam gerektiren bölümler, çok kısa/uzun parçalar.

### 3. Soru üretimi (generator)
- Pasaj başına **1–2 soru**, cevap **kısa span** (isim, tarih, sayı, terim).
- Üretici model: hosted açık kaynak endpoint veya Colab'da çalışan en güçlü model.
- Prompt kuralları: cevap pasajda **birebir geçen bir span** olmalı; soru pasajsız cevaplanamayacak
  kadar pasaja bağlı olmalı; evet/hayır ve muğlak sorular yasak.

### 4. Otomatik filtreler (çözücülerden önce, ucuz eleme)
- **Span kontrolü**: gold cevap normalizasyon sonrası pasajda geçmiyorsa ele.
- **Tekrar/benzerlik**: aynı pasajdan üretilen sorular arası benzerlik eşiği; dataset genelinde dedup.
- **Format**: cevap ≤ ~5 kelime; soru tek soru işareti; pasaja referans ("yukarıdaki metne göre" vb.) temizliği.

### 5. Çözücü grubu (solvers)
- **N = 4–5 açık kaynak model**, karışık güçte (örn. Qwen2.5-7B, Llama-3.1-8B, Gemma-2-9B + 1 küçük model).
- Altyapı: **Colab GPU (T4/L4)** üzerinde vLLM/Ollama, 4-bit quantize; gerekirse ucuz hosted endpoint takviyesi.
- Her model soruyu **pasajla birlikte** (RC modu) cevaplar; cevaplar normalize edilip gold ile exact-match karşılaştırılır.
- Normalizasyon: küçük harf, noktalama/ek boşluk temizliği, Türkçe karakter tutarlılığı; sayılarda rakam/yazı eşleme.

### 6. Bant filtresi + etiketleme
| Çözen model sayısı (N=5) | Karar | Etiket |
|---|---|---|
| 0 | Ele (çözülemez / kötü soru) | — |
| 1 | Ele veya manuel kuyruğa | — |
| 2–3 | Kabul | `hard` / `medium` |
| 4 | Kabul | `easy` |
| 5 | Ele (çok kolay) veya `easy` olarak sınırlı sayıda tut | `trivial` |

- **Gold güvencesi (2 katman)**: (a) span kuralı, (b) çözücüler kendi aralarında tutarlı ama gold'dan
  farklı bir cevapta birleşiyorsa soru elenir (gold muhtemelen hatalı).
- Test split: bant filtresini geçen sorulardan örneklem + **elle gözden geçirme** (pilot ölçeğinde yapılabilir).

### 7. Çıktı
- Ana format **JSONL** (ara aşamalar dahil her aşamanın çıktısı ayrı dosya).
- Yayın: **HF dataset repo** — `train` / `test` split, dataset card (yöntem, kaynaklar, lisanslar, eşikler).

## Veri şeması (final kayıt)
```json
{
  "id": "trwiki-000123-q1",
  "passage": "…200-500 kelimelik metin…",
  "question": "…",
  "answer": "…",
  "answer_aliases": ["…"],
  "source": "tr.wikipedia",
  "source_url": "https://…",
  "license": "CC BY-SA 4.0",
  "difficulty": "medium",
  "solver_results": {"qwen2.5-7b": true, "llama3.1-8b": false, "...": true},
  "solve_rate": 0.6,
  "generator_model": "…",
  "created_at": "2026-07-16"
}
```

## Riskler / açık noktalar
- **Exact-match kırılganlığı**: Türkçe ekler ("Ankara" vs "Ankara'da") — normalizasyon + `answer_aliases` ile çözülür; pilotta hata analizi yapılacak.
- **Çözücü yanlılığı**: çözücüler ne kadar zayıfsa "çözülemez" etiketi o kadar gürültülü; en az bir güçlü model bulundurulmalı.
- **Kontaminasyon**: Wikipedia tüm modellerin eğitiminde var — RC formatı bunu kısmen telafi eder (cevap pasajdan bulunur), yine de closed-book kullanım için uyarı eklenecek.
- **Haber telifi**: lisans netleşmeden haber kaynağı pipeline'a girmeyecek.

## Pilot planı
1. TR Wikipedia'dan ~300 pasaj → uçtan uca pipeline'ı çalıştır (~500 soru adayı).
2. Elde kalan soruların ~50'sini elle incele: gold doğruluğu, soru kalitesi, normalizasyon hataları.
3. Eşikleri (bant, benzerlik, normalizasyon) revize et → 1k hedefine tamamla.
4. HF'e `v0.1` olarak yükle, Datasets.xlsx Turkish sayfasına ekle.
