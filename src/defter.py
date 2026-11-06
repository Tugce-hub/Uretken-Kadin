# -*- coding: utf-8 -*-
"""
Üretken Kadın — satış defteri

Üretici sattığı her ürünü buraya yazar; uygulama ay ve yıl toplamlarını, en çok satan ürünü ve
kârı hesaplar. Hesaplar **yapay zekâ kullanmaz**: formüller açıktır, sayılar üreticinin girdiği
verilerden gelir. Böylece uydurma rakam olmaz.

Kayıt biçimi (hesap belgesindeki "satislar" listesi):
    {"id", "tarih" (ISO: YYYY-AA-GG), "urun", "adet", "birim_fiyat", "birim_maliyet",
     "kanal", "musteri", "notlar"}

Streamlit'e bağımlı değildir (tests/test_defter.py).
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime

KANALLAR = ["Instagram", "WhatsApp", "Trendyol", "Hepsiburada", "Shopier", "Etsy",
            "Elden satış", "Pazar / stant", "Diğer"]
ALANLAR = ("id", "tarih", "urun", "adet", "birim_fiyat", "birim_maliyet", "kanal", "musteri", "notlar")
MAKS_KAYIT = 2000
MAKS_ADET = 100_000
MAKS_TUTAR = 10_000_000
AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz",
         "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]


def yeni_id() -> str:
    return uuid.uuid4().hex[:12]


def _sayi(deger, en_fazla: float) -> float:
    try:
        s = float(str(deger).replace(",", "."))
    except (TypeError, ValueError):
        raise ValueError("Sayı alanlarına rakam yazın.") from None
    if s != s or s in (float("inf"), float("-inf")) or s < 0 or s > en_fazla:
        raise ValueError("Sayı alanları 0 ile " + f"{en_fazla:,.0f}".replace(",", ".") + " arasında olmalı.")
    return round(s, 2)


def _metin(deger, en_fazla: int) -> str:
    return " ".join(str(deger or "").split())[:en_fazla]


def yeni_satis(urun: str, adet, birim_fiyat, birim_maliyet=0, kanal: str = KANALLAR[0],
               tarih: date | str | None = None, musteri: str = "", notlar: str = "") -> dict:
    """Formdan gelen değerleri doğrular ve kayda çevirir. Hatalı girdide ValueError."""
    urun = _metin(urun, 120)
    if len(urun) < 2:
        raise ValueError("Hangi ürünü sattığınızı yazın.")
    adet_s = _sayi(adet, MAKS_ADET)
    if adet_s < 1:
        raise ValueError("Adet en az 1 olmalı.")
    if kanal not in KANALLAR:
        raise ValueError("Satış kanalını seçin.")
    if tarih is None:
        tarih = date.today()
    if isinstance(tarih, datetime):
        tarih = tarih.date()
    if isinstance(tarih, str):
        try:
            tarih = date.fromisoformat(tarih[:10])
        except ValueError:
            raise ValueError("Tarihi gün/ay/yıl olarak seçin.") from None
    return {"id": yeni_id(), "tarih": tarih.isoformat(), "urun": urun, "adet": adet_s,
            "birim_fiyat": _sayi(birim_fiyat, MAKS_TUTAR), "birim_maliyet": _sayi(birim_maliyet, MAKS_TUTAR),
            "kanal": kanal, "musteri": _metin(musteri, 60), "notlar": _metin(notlar, 200)}


def temizle(ham) -> dict | None:
    """Kayıt dosyasından gelen bir satırı doğrular; bozuksa None (içe aktarmada atlanır)."""
    if not isinstance(ham, dict):
        return None
    kanal = ham.get("kanal") if ham.get("kanal") in KANALLAR else KANALLAR[-1]   # bilinmeyen → Diğer
    try:
        kayit = yeni_satis(ham.get("urun"), ham.get("adet"), ham.get("birim_fiyat"),
                           ham.get("birim_maliyet", 0), kanal,
                           ham.get("tarih"), ham.get("musteri", ""), ham.get("notlar", ""))
    except (ValueError, TypeError):
        return None
    kimlik = str(ham.get("id") or "")
    if kimlik.isalnum() and 6 <= len(kimlik) <= 40:
        kayit["id"] = kimlik
    return kayit


# ---------------------------------------------------------------------------
# Hesaplar — hepsi dört işlem; yapay zekâ yok
# ---------------------------------------------------------------------------
def ciro(satis: dict) -> float:
    return round(float(satis.get("adet", 0)) * float(satis.get("birim_fiyat", 0)), 2)


def kar(satis: dict) -> float:
    birim = float(satis.get("birim_fiyat", 0)) - float(satis.get("birim_maliyet", 0))
    return round(float(satis.get("adet", 0)) * birim, 2)


@dataclass(frozen=True)
class Ozet:
    satis_sayisi: int
    adet: float
    ciro: float
    kar: float
    en_cok_urun: tuple[str, float] | None          # (ürün, adet)
    en_cok_kazandiran: tuple[str, float] | None    # (ürün, kâr)
    en_iyi_kanal: tuple[str, float] | None         # (kanal, ciro)
    ortalama_satis: float                          # satış başına ciro


def _aralikta(satislar: list[dict], baslangic: date | None, bitis: date | None) -> list[dict]:
    secili = []
    for s in satislar:
        try:
            g = date.fromisoformat(str(s.get("tarih"))[:10])
        except (TypeError, ValueError):
            continue
        if (baslangic is None or g >= baslangic) and (bitis is None or g <= bitis):
            secili.append(s)
    return secili


def ozet(satislar: list[dict], baslangic: date | None = None, bitis: date | None = None) -> Ozet:
    secili = _aralikta(satislar, baslangic, bitis)
    urun_adet: dict[str, float] = defaultdict(float)
    urun_kar: dict[str, float] = defaultdict(float)
    kanal_ciro: dict[str, float] = defaultdict(float)
    toplam_ciro = toplam_kar = toplam_adet = 0.0
    for s in secili:
        toplam_ciro += ciro(s)
        toplam_kar += kar(s)
        toplam_adet += float(s.get("adet", 0))
        urun_adet[s.get("urun", "—")] += float(s.get("adet", 0))
        urun_kar[s.get("urun", "—")] += kar(s)
        kanal_ciro[s.get("kanal", "Diğer")] += ciro(s)

    def en_buyuk(sozluk):
        return max(sozluk.items(), key=lambda x: x[1]) if sozluk else None

    return Ozet(satis_sayisi=len(secili), adet=round(toplam_adet, 2), ciro=round(toplam_ciro, 2),
                kar=round(toplam_kar, 2), en_cok_urun=en_buyuk(urun_adet),
                en_cok_kazandiran=en_buyuk(urun_kar), en_iyi_kanal=en_buyuk(kanal_ciro),
                ortalama_satis=round(toplam_ciro / len(secili), 2) if secili else 0.0)


def ay_sonu(yil: int, ay: int) -> date:
    sonraki = date(yil + (ay == 12), (ay % 12) + 1, 1)
    return date.fromordinal(sonraki.toordinal() - 1)


def aylik(satislar: list[dict], ay_sayisi: int = 12, bugun: date | None = None) -> list[dict]:
    """Son N ayın ciro ve kâr toplamı; grafik için eskiden yeniye sıralı."""
    bugun = bugun or date.today()
    aylar = []
    yil, ay = bugun.year, bugun.month
    for _ in range(ay_sayisi):
        aylar.append((yil, ay))
        ay -= 1
        if ay == 0:
            yil, ay = yil - 1, 12
    aylar.reverse()
    sonuc = []
    for yil, ay in aylar:
        o = ozet(satislar, date(yil, ay, 1), ay_sonu(yil, ay))
        sonuc.append({"ay": f"{AYLAR[ay - 1][:3]} {str(yil)[2:]}", "ciro": o.ciro, "kâr": o.kar})
    return sonuc


def urun_dokumu(satislar: list[dict]) -> list[dict]:
    """Ürün bazında adet, ciro ve kâr; en çok satandan başlayarak."""
    toplam: dict[str, dict] = {}
    for s in satislar:
        ad = s.get("urun", "—")
        kayit = toplam.setdefault(ad, {"ürün": ad, "adet": 0.0, "ciro": 0.0, "kâr": 0.0})
        kayit["adet"] += float(s.get("adet", 0))
        kayit["ciro"] += ciro(s)
        kayit["kâr"] += kar(s)
    for k in toplam.values():
        k["adet"], k["ciro"], k["kâr"] = round(k["adet"], 2), round(k["ciro"], 2), round(k["kâr"], 2)
    return sorted(toplam.values(), key=lambda k: (-k["adet"], -k["ciro"]))


def _tl(tutar: float) -> str:
    return f"{tutar:,.0f}".replace(",", ".") + " TL"


def icgoruler(satislar: list[dict], bugun: date | None = None) -> list[str]:
    """Sayılardan çıkan, uydurmasız kısa yorumlar."""
    bugun = bugun or date.today()
    if not satislar:
        return []
    bu_ay_bas = bugun.replace(day=1)
    onceki_son = date.fromordinal(bu_ay_bas.toordinal() - 1)
    onceki_bas = onceki_son.replace(day=1)
    bu_ay = ozet(satislar, bu_ay_bas, ay_sonu(bugun.year, bugun.month))
    gecen_ay = ozet(satislar, onceki_bas, onceki_son)
    notlar = []

    if bu_ay.satis_sayisi:
        notlar.append(f"Bu ay {bu_ay.satis_sayisi} satış kaydettiniz: {_tl(bu_ay.ciro)} ciro, "
                      f"{_tl(bu_ay.kar)} kâr.")
        if bu_ay.en_cok_urun:
            ad, adet = bu_ay.en_cok_urun
            notlar.append(f"En çok satan ürününüz **{ad}** ({adet:g} adet).")
        if (bu_ay.en_cok_kazandiran and bu_ay.en_cok_urun
                and bu_ay.en_cok_kazandiran[0] != bu_ay.en_cok_urun[0]):
            ad, k = bu_ay.en_cok_kazandiran
            notlar.append(f"En çok kazandıran ürün **{ad}**: {_tl(k)} kâr.")
        if bu_ay.en_iyi_kanal and bu_ay.ciro:
            kanal, tutar = bu_ay.en_iyi_kanal
            notlar.append(f"Satışınızın %{round(100 * tutar / bu_ay.ciro)}'i **{kanal}** üzerinden geldi.")
    else:
        notlar.append("Bu ay henüz satış kaydetmediniz.")

    if gecen_ay.ciro:
        fark = round(100 * (bu_ay.ciro - gecen_ay.ciro) / gecen_ay.ciro)
        if fark > 5:
            notlar.append(f"Geçen aya göre ciro **%{fark} arttı** "
                          f"({_tl(gecen_ay.ciro)} → {_tl(bu_ay.ciro)}).")
        elif fark < -5:
            notlar.append(f"Geçen aya göre ciro **%{abs(fark)} azaldı** "
                          f"({_tl(gecen_ay.ciro)} → {_tl(bu_ay.ciro)}).")

    zararli = [k["ürün"] for k in urun_dokumu(satislar) if k["kâr"] < 0]
    if zararli:
        notlar.append("Zararına görünen ürün: **" + ", ".join(zararli[:3])
                      + "**. Maliyeti ya da fiyatı gözden geçirin.")
    return notlar
