import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="BIST Quant Radar", layout="wide")
st.title("📊 BIST Nicel Mikroyapı Radarı")

if os.path.exists("sonuclar.csv"):
    df = pd.read_csv("sonuclar.csv")
    st.metric("Taranan Hisse", len(df))

    # Sütun düzenleme ve isimlendirme
    cols = ['ticker', 'quant_score', 'prev_quant_score', 'score_diff', 'rvol_ratio', 'pct_hhi', 'change_%']
    names = ['Hisse', 'Bugünkü Skor', 'Dünkü Skor', 'Skor Farkı', 'RVOL', 'HHI Dilimi', 'Değişim %']

    # 1. TABLO: EN YÜKSEK SKORLAR
    st.subheader("🚀 En Yüksek Quant Skorlu Hisseler (Top 20)")
    top_df = df.head(20)[cols].copy()
    top_df.columns = names
    st.dataframe(top_df.style.background_gradient(subset=['Bugünkü Skor'], cmap='RdYlGn'), use_container_width=True)

    # 2. TABLO: EN ÇOK DÜŞENLER
    st.subheader("📉 Skoru En Çok Düşen Hisseler (Güç Kaybedenler)")
    loser_df = df.sort_values(by='score_diff', ascending=True).head(10)[cols].copy()
    loser_df.columns = names
    st.dataframe(loser_df.style.background_gradient(subset=['Skor Farkı'], cmap='Reds'), use_container_width=True)
    
    st.caption("💡 RVOL > 1.0 ise hacim artışı, Skor Farkı pozitifse nicel güçlenme var demektir.")
else:
    st.info("Veri bekleniyor...")
