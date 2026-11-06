# -*- coding: utf-8 -*-
"""
Üretken Kadın — "Nasıl kullanılır?" tanıtım videosu

Video varsayılan olarak uygulamayla birlikte gelir (src/assets/tanitim.mp4, ~2 MB) ve alt yazısı
(tanitim.srt) oynatıcıdan açılabilir. Dışarıda barındırmak isterseniz (YouTube vb.) TANITIM_VIDEO
ortam değişkenine bağlantıyı yazın; o zaman bağlantı kullanılır.

Dosya yoksa ve ortam değişkeni de tanımlı değilse video bölümü hiç gösterilmez — uygulama bozulmaz.
"""

from __future__ import annotations

import os
from pathlib import Path

import streamlit as st

KLASOR = Path(__file__).resolve().parent / "assets"
VIDEO_DOSYASI = KLASOR / "tanitim.mp4"
ALTYAZI_DOSYASI = KLASOR / "tanitim.srt"
SURE = "1,5 dakika"
ETIKET = f"▶️ Nasıl kullanılır? ({SURE})"


def kaynak() -> str | None:
    """Oynatılacak video: önce ortam değişkeni (bağlantı), yoksa uygulamayla gelen dosya."""
    adres = os.getenv("TANITIM_VIDEO", "").strip()
    if adres:
        return adres
    return str(VIDEO_DOSYASI) if VIDEO_DOSYASI.exists() else None


def var_mi() -> bool:
    return kaynak() is not None


def oynat() -> None:
    """Videoyu (varsa alt yazısıyla) gösterir."""
    yol = kaynak()
    if not yol:
        return
    altyazi = ALTYAZI_DOSYASI if (ALTYAZI_DOSYASI.exists() and not yol.startswith("http")) else None
    try:
        st.video(yol, subtitles={"Türkçe": altyazi} if altyazi else None)
    except Exception:                      # eski Streamlit sürümünde alt yazı desteklenmeyebilir
        st.video(yol)
    st.caption("Alt yazı için oynatıcıdaki **CC** düğmesine dokunun. Videoda hesap açmaktan "
               "içerik hazırlamaya kadar tüm adımlar var.")


def dugme(anahtar: str, etiket: str = ETIKET) -> None:
    """Videoyu açıp kapatan düğme; video yoksa hiçbir şey çizmez."""
    if not var_mi():
        return
    durum = f"{anahtar}_acik"
    acik = bool(st.session_state.get(durum))
    if st.button("✖️ Videoyu kapat" if acik else etiket, key=anahtar, use_container_width=True):
        st.session_state[durum] = not acik
        st.rerun()
    if st.session_state.get(durum):
        oynat()
