# -*- coding: utf-8 -*-
"""
defter.py testleri — satış kaydı, toplamlar ve içgörüler. Yapay zekâ ve internet gerektirmez.

    python tests/test_defter.py
"""
import os
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import defter  # noqa: E402

BUGUN = date(2026, 11, 20)


def satis(urun="Vişne reçeli", adet=2, fiyat=150, maliyet=90, kanal="Instagram", gun="2026-11-10"):
    return defter.yeni_satis(urun, adet, fiyat, maliyet, kanal, gun)


def _hata_bekle(fonk, *arg, **kw):
    try:
        fonk(*arg, **kw)
    except ValueError:
        return
    raise AssertionError("ValueError bekleniyordu")


# ---------------------------------------------------------------- kayıt
def test_yeni_satis_dogrular_ve_temizler():
    s = defter.yeni_satis("  Vişne   reçeli ", "3", "150,5", 90, "WhatsApp", date(2026, 11, 5),
                          musteri="Ayşe H.", notlar="hediye paketi")
    assert s["urun"] == "Vişne reçeli" and s["adet"] == 3 and s["birim_fiyat"] == 150.5
    assert s["tarih"] == "2026-11-05" and s["kanal"] == "WhatsApp" and len(s["id"]) == 12
    assert defter.ciro(s) == 451.5 and defter.kar(s) == 181.5

    _hata_bekle(defter.yeni_satis, "x", 1, 10)                       # ürün adı kısa
    _hata_bekle(defter.yeni_satis, "Reçel", 0, 10)                   # adet sıfır
    _hata_bekle(defter.yeni_satis, "Reçel", 1, -5)                   # eksi fiyat
    _hata_bekle(defter.yeni_satis, "Reçel", 1, 10, 0, "Uydurma kanal")
    _hata_bekle(defter.yeni_satis, "Reçel", "abc", 10)
    _hata_bekle(defter.yeni_satis, "Reçel", 1, 10, 0, "Instagram", "20.11.2026")


def test_temizle_bozuk_kaydi_atlar_kimligi_korur():
    ham = {"id": "abc123def456", "urun": "Keçe patik", "adet": 2, "birim_fiyat": 300,
           "birim_maliyet": 120, "kanal": "Shopier", "tarih": "2026-10-02"}
    kayit = defter.temizle(ham)
    assert kayit["id"] == "abc123def456" and kayit["kanal"] == "Shopier"
    assert defter.temizle({"urun": "x", "adet": 1, "birim_fiyat": 1}) is None     # ürün adı kısa
    assert defter.temizle("metin") is None
    bilinmeyen = defter.temizle({"urun": "Sabun", "adet": 1, "birim_fiyat": 50, "kanal": "Pazaryeri X"})
    assert bilinmeyen["kanal"] == "Diğer"                                          # bilinmeyen kanal


# ---------------------------------------------------------------- toplamlar
def test_ozet_ciro_kar_ve_en_cok_satan():
    satislar = [satis(adet=2), satis("Keçe patik", 5, 200, 80, "Shopier", "2026-11-12"),
                satis("Vişne reçeli", 3, 150, 90, "Instagram", "2026-10-20")]
    kasim = defter.ozet(satislar, date(2026, 11, 1), BUGUN)
    assert kasim.satis_sayisi == 2 and kasim.adet == 7
    assert kasim.ciro == 2 * 150 + 5 * 200 and kasim.kar == 2 * 60 + 5 * 120
    assert kasim.en_cok_urun == ("Keçe patik", 5) and kasim.en_iyi_kanal == ("Shopier", 1000)
    assert kasim.ortalama_satis == round(1300 / 2, 2)

    tumu = defter.ozet(satislar)
    assert tumu.satis_sayisi == 3 and tumu.ciro == 1750
    assert defter.ozet([]).satis_sayisi == 0 and defter.ozet([]).en_cok_urun is None


def test_aylik_seri_ve_urun_dokumu():
    satislar = [satis(gun="2026-11-10"), satis("Sabun", 4, 100, 60, "Shopier", "2026-09-03")]
    seri = defter.aylik(satislar, 3, BUGUN)
    assert [a["ay"] for a in seri] == ["Eyl 26", "Eki 26", "Kas 26"]
    assert seri[0]["ciro"] == 400 and seri[1]["ciro"] == 0 and seri[2]["ciro"] == 300

    dokum = defter.urun_dokumu(satislar)
    assert [k["ürün"] for k in dokum] == ["Sabun", "Vişne reçeli"]      # adede göre sıralı
    assert dokum[0]["kâr"] == 160 and dokum[1]["ciro"] == 300


# ---------------------------------------------------------------- içgörüler
def test_ozet_ay_sonuna_kadar_sayar():
    # bugünden sonraki ama aynı aydaki kayıt da bu ayın toplamına girer
    ileri = [satis(adet=1, fiyat=200, gun="2026-11-28")]
    o = defter.ozet(ileri, date(2026, 11, 1), defter.ay_sonu(2026, 11))
    assert o.ciro == 200 and defter.ay_sonu(2026, 2) == date(2026, 2, 28)


def test_icgoruler_sayilara_dayanir():
    satislar = [satis(adet=2, gun="2026-11-10"),                       # bu ay: 300 ciro, 120 kâr
                satis("Keçe patik", 1, 500, 100, "Shopier", "2026-11-15"),
                satis("Vişne reçeli", 1, 150, 90, "Instagram", "2026-10-05")]   # geçen ay: 150
    notlar = " ".join(defter.icgoruler(satislar, BUGUN))
    assert "3 satış" not in notlar and "2 satış" in notlar
    assert "800 TL ciro" in notlar and "Keçe patik" in notlar
    assert "arttı" in notlar                                            # 150 → 800
    assert defter.icgoruler([], BUGUN) == []
    assert "henüz satış kaydetmediniz" in " ".join(defter.icgoruler([satis(gun="2026-09-01")], BUGUN))


def test_zararina_satis_uyarisi():
    notlar = " ".join(defter.icgoruler([satis("Zararlı ürün", 1, 50, 120, "Instagram", "2026-11-11")], BUGUN))
    assert "Zararına görünen ürün" in notlar and "Zararlı ürün" in notlar


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
