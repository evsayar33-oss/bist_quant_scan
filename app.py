import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="BIST Quant Terminal", layout="wide")
st.title("📊 BIST Nicel Mikroyapı Terminali")

if os.path.exists("sonuclar.csv"):
    df = pd.read_csv("sonuclar.csv")
    
    # Sayıları yuvarla
    for col in ['quant_score', 'prev_quant_score', 'score_diff', 'rvol_ratio', 'pct_hhi', 'change_%']:
        if col in df.columns:
            df[col] = df[col].round(2)

    cols = ['ticker', 'quant_score', 'prev_quant_score', 'score_diff', 'rvol_ratio', 'pct_hhi', 'change_%']
    names = ['Hisse', 'Skor', 'Dün', 'Fark', 'RVOL', 'HHI %', 'Fiyat %']

    st.subheader("🏆 Genel Nicel Liderler (Top 20)")
    st.dataframe(df.head(20)[cols].rename(columns=dict(zip(cols, names))).style.background_gradient(subset=['Skor'], cmap='RdYlGn'), use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🚀 Atak Yapanlar")
        gainers = df[df['score_diff'] > 0.1].sort_values(by='score_diff', ascending=False).head(10)
        if not gainers.empty:
            st.dataframe(gainers[cols].rename(columns=dict(zip(cols, names))).style.background_gradient(subset=['Fark'], cmap='Greens'), use_container_width=True)
        else:
            st.info("Kıyaslanabilir skor artışı henüz oluşmadı.")

    with c2:
        st.subheader("⚠️ Güç Kaybedenler")
        losers = df[df['score_diff'] < -0.1].sort_values(by='score_diff', ascending=True).head(10)
        if not losers.empty:
            st.dataframe(losers[cols].rename(columns=dict(zip(cols, names))).style.background_gradient(subset=['Fark'], cmap='Reds_r'), use_container_width=True)
        else:
            st.info("Kıyaslanabilir skor düşüşü henüz oluşmadı.")
else:
    st.info("Veri bekleniyor...")
