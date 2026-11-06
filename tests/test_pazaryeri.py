# -*- coding: utf-8 -*-
"""
pazaryeri.py testleri — üreticinin girdiği kesintiler. Uydurma oran yok; her şey kullanıcıdan gelir.

    python tests/test_pazaryeri.py
"""
import os
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import pazaryeri  # noqa: E402
import satis  # noqa: E402


def _hata_bekle(fonk, *arg, **kw):
    try:
        fonk(*arg, **kw)
    except ValueError:
        return
    raise AssertionError("ValueError bekleniyordu")


def test_varsayilan_oran_yok():
    """Uygulama hiçbir platform için hazır komisyon oranı taşımamalı."""
    assert pazaryeri.ayar({}, "Trendyol") is None
    for platform in pazaryeri.PLATFORMLAR:
        assert platform in pazaryeri.NEREDE_YAZAR                    # yerini tarif ediyoruz, oranı değil


def test_ayar_olustur_dogrular():
    a = pazaryeri.ayar_olustur("17,5", 11.4, 0, "  kadın girişimci  ", "2026-11-06")
    assert a == {"komisyon_yuzde": 17.5, "sabit_kesinti": 11.4, "kargo": 0.0,
                 "notlar": "kadın girişimci", "guncelleme": "2026-11-06"}
    assert pazaryeri.ayar_olustur(0)["guncelleme"] == date.today().isoformat()
    _hata_bekle(pazaryeri.ayar_olustur, 100)
    _hata_bekle(pazaryeri.ayar_olustur, -1)
    _hata_bekle(pazaryeri.ayar_olustur, "abc")
    _hata_bekle(pazaryeri.ayar_olustur, 10, -5)


def test_temizle_bilinmeyen_platformu_ve_bozuk_kaydi_atar():
    ham = {"Trendyol": {"komisyon_yuzde": 12, "sabit_kesinti": 5, "guncelleme": "2026-01-02"},
           "Pazaryeri X": {"komisyon_yuzde": 10},
           "Shopier": {"komisyon_yuzde": "çok"},
           "Etsy": "metin"}
    temiz = pazaryeri.temizle(ham)
    assert list(temiz) == ["Trendyol"] and temiz["Trendyol"]["komisyon_yuzde"] == 12
    assert pazaryeri.temizle(None) == {}


def test_eskimis_ayar_uyarilir():
    yeni = pazaryeri.ayar_olustur(10, guncelleme="2026-11-01")
    eski = pazaryeri.ayar_olustur(10, guncelleme="2026-01-01")
    bugun = date(2026, 11, 6)
    assert not pazaryeri.eskimis_mi(yeni, bugun=bugun) and pazaryeri.eskimis_mi(eski, bugun=bugun)
    assert pazaryeri.eskimis_mi({"guncelleme": "bozuk"}, bugun=bugun)


def test_ozet_satiri_okunakli():
    metin = pazaryeri.ozet_satiri(pazaryeri.ayar_olustur(17.5, 11.4, 30, "", "2026-11-06"))
    assert "%17,5 komisyon" in metin and "11,4 TL sabit kesinti" in metin and "06.11.2026" in metin


def test_kadin_destegi_metni_resmi_kaynaktan():
    assert "17 Şubat 2027" in pazaryeri.KADIN_DESTEGI and "%0" in pazaryeri.KADIN_DESTEGI
    assert pazaryeri.KADIN_DESTEGI_KAYNAK.startswith("https://www.trendyol.com/")


def test_sabit_kesinti_fiyata_yansir():
    temel = satis.FiyatGirdisi(malzeme=70, emek_saat=2, saat_ucreti=150, ambalaj=15,
                               komisyon_yuzde=20, kar_yuzde=25)
    kesintili = satis.FiyatGirdisi(malzeme=70, emek_saat=2, saat_ucreti=150, ambalaj=15,
                                   komisyon_yuzde=20, kar_yuzde=25, sabit_kesinti=12)
    assert satis.fiyat_oner(kesintili).satis_fiyati > satis.fiyat_oner(temel).satis_fiyati
    d = satis.dokum(kesintili, 620)
    assert d.sabit_kesinti == 12 and d.eline_gecen == round(620 - 124 - 12, 2)


if __name__ == "__main__":
    testler = [(ad, f) for ad, f in sorted(globals().items()) if ad.startswith("test_")]
    hatali = 0
    for ad, f in testler:
        try:
            f()
            print(f"  OK    {ad}")
        except Exception as hata:
            hatali += 1
            print(f"  HATA  {ad}: {hata!r}")
    print(f"\n{len(testler) - hatali}/{len(testler)} test geçti")
    sys.exit(1 if hatali else 0)
