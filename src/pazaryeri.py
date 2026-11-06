# -*- coding: utf-8 -*-
"""
Üretken Kadın — pazaryeri kesintileri (üreticinin kendi girdiği oranlar)

Önemli ilke: **komisyon oranı uydurulmaz.** Pazaryerlerinin oranları kategoriye, satıcı seviyesine
ve döneme göre değişir; herkese açık güvenilir bir liste yoktur. Bu yüzden oranları üretici bir kez
kendi satıcı panelinden bakıp girer, biz hesabında saklarız ve o değiştirene kadar aynı oranları
kullanırız. Her ayarın yanında en son ne zaman güncellendiği durur.

Kayıt biçimi (hesap belgesindeki "pazaryerleri" sözlüğü):
    {"Trendyol": {"komisyon_yuzde": 17.5, "sabit_kesinti": 11.4, "kargo": 0.0,
                  "guncelleme": "2026-11-06", "not": ""}}

Streamlit'e bağımlı değildir (tests/test_pazaryeri.py).
"""

from __future__ import annotations

import math
from datetime import date

# Üreticinin satabileceği yerler. "Kendi satışım" komisyonsuz (elden, WhatsApp, kendi sitesi).
PLATFORMLAR = ["Kendi satışım", "Trendyol", "Hepsiburada", "Shopier", "Etsy"]

# Oranı panelde nerede bulacağına dair yol tarifi (oranın kendisi değil, yeri).
NEREDE_YAZAR = {
    "Trendyol": "Trendyol Satıcı Paneli → Finans → Komisyon Oranları (kategori kırılımıyla listelenir). "
                "Kargo ve hizmet/işlem bedelleri Finans → Hakediş ekranındaki kesinti satırlarında görünür.",
    "Hepsiburada": "Hepsiburada İş Ortağım paneli → Finans → Komisyon ve Hizmet Bedelleri. "
                   "Komisyonlar KDV hariç ilan edilir; hakediş ekranında KDV'li tutarı görürsünüz.",
    "Shopier": "Shopier paneli → Ayarlar / Ödemeler → İşlem ücretleri. Oran satış hacmine ve ödeme "
               "tipine (tek çekim, taksit, havale) göre değişebilir.",
    "Etsy": "Etsy Shop Manager → Finances → Payment account. Listeleme ücreti, işlem ücreti ve ödeme "
            "işlem ücreti ayrı satırlardır.",
    "Kendi satışım": "Elden, WhatsApp ya da kendi sitenizden satışta pazaryeri komisyonu olmaz; "
                     "yalnızca varsa ödeme/sanal POS kesintisini yazın.",
}

# Trendyol'un kendi sayfasındaki resmî açıklama (06.11.2026'da trendyol.com/s/is-ortaklarina-ozel
# adresinden alındı). Oran uydurmuyoruz; doğrudan aktarıyoruz.
KADIN_DESTEGI_KAYNAK = "https://www.trendyol.com/s/is-ortaklarina-ozel"
KADIN_DESTEGI_TARIH = "06.11.2026"
KADIN_DESTEGI = (
    "**Trendyol'da kadın girişimci ve kadın kooperatifi desteği**\n\n"
    "- **Kadın Girişimci:** gerçek kişilerde kadın satıcılar, şirketlerde ise en az %51'i kadınlara "
    "ait olanlar. Komisyon, ilk ürün listelemeden itibaren net ciro 200.000 TL'ye ulaşana kadar "
    "Komisyon Oranı Tablosu'ndaki \"Kadın Girişimci\" oranlarından hesaplanır.\n"
    "- **Kadın Kooperatifi:** en az %51'i kadınlara ait kooperatifler, yalnızca kendi ürettiği/işlediği "
    "ürünleri satıyorsa ve paketli-barkodlu en az bir ürünü varsa komisyon **17 Şubat 2027'ye kadar %0**, "
    "ardından 26 Temmuz 2031'e kadar **%1** olarak hesaplanır.\n\n"
    f"Kaynak: Trendyol İş Ortaklarına Özel sayfası ({KADIN_DESTEGI_TARIH} tarihinde okundu). "
    "Kendi durumunuzu satıcı panelinizden doğrulayın."
)

MAKS_TUTAR = 1_000_000


def _sayi(deger, ad: str, en_fazla: float) -> float:
    try:
        s = float(str(deger).replace(",", "."))
    except (TypeError, ValueError):
        raise ValueError(f"{ad} alanına rakam yazın.") from None
    if not math.isfinite(s) or s < 0 or s > en_fazla:
        raise ValueError(f"{ad} 0 ile {en_fazla:,.0f} arasında olmalı.".replace(",", "."))
    return round(s, 2)


def ayar_olustur(komisyon_yuzde, sabit_kesinti=0, kargo=0, notlar: str = "",
                 guncelleme: date | str | None = None) -> dict:
    """Üreticinin girdiği kesintileri doğrular ve kayda çevirir."""
    komisyon = _sayi(komisyon_yuzde, "Komisyon", 100)
    if komisyon >= 100:
        raise ValueError("Komisyon %100'den küçük olmalı.")
    if guncelleme is None:
        guncelleme = date.today()
    if isinstance(guncelleme, str):
        try:
            guncelleme = date.fromisoformat(guncelleme[:10])
        except ValueError:
            guncelleme = date.today()
    return {"komisyon_yuzde": komisyon,
            "sabit_kesinti": _sayi(sabit_kesinti, "Sabit kesinti", MAKS_TUTAR),
            "kargo": _sayi(kargo, "Kargo", MAKS_TUTAR),
            "notlar": " ".join(str(notlar or "").split())[:200],
            "guncelleme": guncelleme.isoformat()}


def temizle(ham) -> dict[str, dict]:
    """Kayıt dosyasından gelen pazaryeri ayarlarını doğrular; bozuk satırları atar."""
    if not isinstance(ham, dict):
        return {}
    sonuc = {}
    for platform, ayar in list(ham.items())[:20]:
        if platform not in PLATFORMLAR or not isinstance(ayar, dict):
            continue
        try:
            sonuc[platform] = ayar_olustur(ayar.get("komisyon_yuzde", 0), ayar.get("sabit_kesinti", 0),
                                           ayar.get("kargo", 0), ayar.get("notlar", ""),
                                           ayar.get("guncelleme"))
        except (ValueError, TypeError):
            continue
    return sonuc


def ayar(ayarlar: dict, platform: str) -> dict | None:
    """Kayıtlı ayar varsa döndürür; yoksa None (kullanıcıdan istenir)."""
    kayit = (ayarlar or {}).get(platform)
    return kayit if isinstance(kayit, dict) else None


def eskimis_mi(kayit: dict, gun: int = 180, bugun: date | None = None) -> bool:
    """Oranlar sık değişir; 6 aydan eski ayar için 'kontrol edin' uyarısı gösterilir."""
    try:
        yazilma = date.fromisoformat(str(kayit.get("guncelleme"))[:10])
    except (TypeError, ValueError):
        return True
    return ((bugun or date.today()) - yazilma).days > gun


def ozet_satiri(kayit: dict) -> str:
    """Ayarı tek satırda özetler: '%17,5 komisyon · 11,4 TL sabit kesinti · 06.11.2026'."""
    parcalar = [f"%{kayit['komisyon_yuzde']:g} komisyon".replace(".", ",")]
    if kayit.get("sabit_kesinti"):
        parcalar.append(f"{kayit['sabit_kesinti']:g} TL sabit kesinti".replace(".", ","))
    if kayit.get("kargo"):
        parcalar.append(f"{kayit['kargo']:g} TL kargo".replace(".", ","))
    try:
        gun = date.fromisoformat(str(kayit.get("guncelleme"))[:10])
        parcalar.append(f"{gun:%d.%m.%Y} tarihinde girildi")
    except (TypeError, ValueError):
        pass
    return " · ".join(parcalar)
