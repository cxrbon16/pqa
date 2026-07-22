"""Türkçe'ye duyarlı cevap normalizasyonu ve exact-match karşılaştırma."""
import re

_TR_MAP = str.maketrans({"I": "ı", "İ": "i"})
_PUNCT_RE = re.compile(r"[^\w\s]", re.UNICODE)
_WS_RE = re.compile(r"\s+")


def tr_lower(s):
    return s.translate(_TR_MAP).lower()


def norm(s):
    s = tr_lower(str(s).strip())
    s = _PUNCT_RE.sub(" ", s)
    return _WS_RE.sub(" ", s).strip()


def _stem_eq(a, b):
    """Hafif ek toleransı: 'ankara' vs 'ankarada' gibi kısa ek farklarını eşle."""
    if not a or not b:
        return False
    longer, shorter = (a, b) if len(a) >= len(b) else (b, a)
    return len(shorter) >= 4 and longer.startswith(shorter) and len(longer) - len(shorter) <= 4


def _words_stem_eq(a, b):
    aw, bw = a.split(), b.split()
    if len(aw) != len(bw):
        return False
    return all(x == y or _stem_eq(x, y) for x, y in zip(aw, bw))


def contains_span(text, span):
    """Normalize edilmiş metinde span kelime sınırlarıyla geçiyor mu."""
    t, s = norm(text), norm(span)
    if not s:
        return False
    return re.search(r"(?:^|\s)" + re.escape(s) + r"(?:\s|$)", t) is not None


def is_match(gold, aliases, pred, max_pred_words=8):
    """Model cevabı gold veya alias'lardan biriyle eşleşiyor mu."""
    p = norm(pred)
    if not p:
        return False
    for cand in [gold] + list(aliases or []):
        g = norm(cand)
        if not g:
            continue
        if p == g or _words_stem_eq(p, g):
            return True
        # kısa bir cevabın içinde gold geçiyorsa kabul ("başkent ankara" ~ "ankara")
        if len(p.split()) <= max_pred_words and contains_span(p, g):
            return True
    return False
