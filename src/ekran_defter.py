# -*- coding: utf-8 -*-
"""
Üretken Kadın — Satış defteri ekranı

Üretici sattığı ürünü kaydeder; uygulama ay/yıl toplamlarını, en çok satanı ve kârı gösterir.
Kayıtlar hesapla birlikte saklanır (st.session_state.satislar → hesap belgesindeki "satislar").
"""

from __future__ import annotations

import html
from dataclasses import dataclass
from datetime import date
from typing import Callable

import pandas as pd
import streamlit as st

import defter
import takvim

VARSAYILANLAR = {"satislar": [], "df_mesaj": None}


@dataclass
class Baglam:
    ust_bar: Callable[[], None]
    git: Callable[[str], None]


def _tl(tutar: float) -> str:
    return f"{tutar:,.0f}".replace(",", ".") + " TL"


def _kutu(deger: str, etiket: str) -> str:
    return f'<div class="kutu"><div class="deger">{html.escape(deger)}</div>' \
           f'<div class="etiket">{html.escape(etiket)}</div></div>'


def _urun_adlari() -> list[str]:
    """Hazırlanan içeriklerden ürün adı önerileri (başlık) + defterde geçen adlar."""
    adlar = []
    for k in st.session_state.get("gecmis", []):
        baslik = takvim.baslik_uret(k.get("anlatim", ""))
        if baslik and baslik not in adlar:
            adlar.append(baslik)
    for s in st.session_state.get("satislar", []):
        if s.get("urun") and s["urun"] not in adlar:
            adlar.append(s["urun"])
    return adlar


def _kayit_formu() -> None:
    adlar = _urun_adlari()
    with st.form("satis_formu", border=False):
        k1, k2 = st.columns([2, 1])
        if adlar:
            secim = k1.selectbox("Hangi ürünü sattınız?", ["✍️ Yeni ürün yaz"] + adlar, key="df_urun_secim")
            urun = (k1.text_input("Ürün adı", key="df_urun_yeni", placeholder="Vişne reçeli 350 g")
                    if secim == "✍️ Yeni ürün yaz" else secim)
        else:
            urun = k1.text_input("Hangi ürünü sattınız?", key="df_urun_yeni",
                                 placeholder="Vişne reçeli 350 g")
        tarih = k2.date_input("Satış tarihi", value=takvim.simdi().date(),
                              max_value=takvim.simdi().date(), format="DD.MM.YYYY", key="df_tarih")

        s1, s2, s3 = st.columns(3)
        adet = s1.number_input("Adet", min_value=1.0, value=1.0, step=1.0, key="df_adet")
        fiyat = s2.number_input("Birim satış fiyatı (TL)", min_value=0.0, value=0.0, step=10.0,
                                key="df_fiyat")
        maliyet = s3.number_input("Birim maliyet (TL)", min_value=0.0, value=0.0, step=10.0,
                                  key="df_maliyet",
                                  help="Malzeme + ambalaj + emeğiniz. Fiyat hesaplayıcıdaki "
                                       "maliyeti buraya yazabilirsiniz; boş bırakırsanız kâr "
                                       "hesaplanmaz.")
        k3, k4 = st.columns(2)
        kanal = k3.selectbox("Nereden sattınız?", defter.KANALLAR, key="df_kanal")
        musteri = k4.text_input("Müşteri (isteğe bağlı)", key="df_musteri",
                                placeholder="Yalnızca siz görürsünüz")
        notlar = st.text_input("Not (isteğe bağlı)", key="df_notlar",
                               placeholder="Hediye paketi istedi, kargoyu o ödedi…")
        kaydet = st.form_submit_button("➕ Satışı kaydet", type="primary", use_container_width=True)

    if kaydet:
        try:
            kayit = defter.yeni_satis(urun, adet, fiyat, maliyet, kanal, tarih, musteri, notlar)
        except ValueError as hata:
            st.error(str(hata))
            return
        st.session_state.satislar = [kayit] + list(st.session_state.satislar)
        st.session_state.df_mesaj = f"✅ Kaydedildi: {kayit['urun']} · {_tl(defter.ciro(kayit))}"
        st.rerun()


def _ozet_karti(o: defter.Ozet, baslik: str) -> None:
    st.markdown(f'<div class="gun-baslik">{html.escape(baslik)}</div>', unsafe_allow_html=True)
    st.markdown('<div class="ozet">'
                + _kutu(_tl(o.ciro), "ciro")
                + _kutu(_tl(o.kar), "kâr")
                + _kutu(f"{o.satis_sayisi:g}", "satış")
                + "</div>", unsafe_allow_html=True)


def _liste(satislar: list[dict]) -> None:
    st.markdown('<div class="kart-baslik" style="margin-top:1.2rem">🧾 Son satışlar</div>',
                unsafe_allow_html=True)
    for s in satislar[:30]:
        k1, k2 = st.columns([6, 1], vertical_alignment="center")
        gun = date.fromisoformat(s["tarih"])
        satir = (f'<div class="satis-satiri"><b>{html.escape(s["urun"])}</b>'
                 f'<span class="kucuk">{gun.day} {defter.AYLAR[gun.month - 1]} · {s["adet"]:g} adet · '
                 f'{html.escape(s["kanal"])}</span>'
                 f'<span class="tutar">{_tl(defter.ciro(s))}</span></div>')
        k1.markdown(satir, unsafe_allow_html=True)
        if k2.button("🗑️", key=f"df_sil_{s['id']}", help="Bu kaydı sil"):
            st.session_state.satislar = [x for x in st.session_state.satislar if x["id"] != s["id"]]
            st.session_state.df_mesaj = "Kayıt silindi."
            st.rerun()
    if len(satislar) > 30:
        st.caption(f"Son 30 satış gösteriliyor; defterinizde toplam {len(satislar)} kayıt var.")


def satis_defteri(b: Baglam) -> None:
    b.ust_bar()
    st.markdown('<div class="ekran-baslik">Satış defteri <span class="yumak" aria-hidden="true">📒</span></div>',
                unsafe_allow_html=True)
    st.markdown('<div class="ekran-alt">Her sattığınızı buraya yazın; ay sonunda ne kadar sattığınızı, '
                'neyin daha çok kazandırdığını kendiliğinden görün.</div>', unsafe_allow_html=True)

    if st.session_state.df_mesaj:
        st.success(st.session_state.df_mesaj)
        st.session_state.df_mesaj = None

    _kayit_formu()

    satislar = st.session_state.satislar
    if not satislar:
        st.markdown('<div class="bos"><div class="ik">📒</div><p>Defteriniz henüz boş. '
                    'İlk satışınızı yukarıdan ekleyin.</p></div>', unsafe_allow_html=True)
        return

    bugun = takvim.simdi().date()
    ay_bas, ay_son = bugun.replace(day=1), defter.ay_sonu(bugun.year, bugun.month)
    _ozet_karti(defter.ozet(satislar, ay_bas, ay_son), f"{defter.AYLAR[bugun.month - 1]} {bugun.year}")
    _ozet_karti(defter.ozet(satislar, date(bugun.year, 1, 1), date(bugun.year, 12, 31)),
                f"{bugun.year} yılı")

    for not_metni in defter.icgoruler(satislar, bugun):
        st.markdown(f"- {not_metni}")

    seri = defter.aylik(satislar, 6, bugun)
    if any(a["ciro"] for a in seri):
        st.markdown('<div class="kart-baslik" style="margin-top:1.2rem">📈 Son 6 ay</div>',
                    unsafe_allow_html=True)
        st.bar_chart(pd.DataFrame(seri).set_index("ay"), color=["#27348B", "#3FB59E"])

    dokum = defter.urun_dokumu(satislar)
    if dokum:
        st.markdown('<div class="kart-baslik">🏆 Ürünleriniz</div>', unsafe_allow_html=True)
        st.dataframe(pd.DataFrame(dokum), hide_index=True, use_container_width=True)

    _liste(satislar)
    st.caption("Kayıtlar hesabınızda saklanır; Hesabım sayfasından tüm verilerinizi indirebilirsiniz.")
