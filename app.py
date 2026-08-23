import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="BIST Institutional Radar", layout="wide")
st.title("🛡️ BIST Kurumsal Akış & Gatekeeper")

if os.path.exists("sonuclar.csv"):
    df = pd.read_csv("sonuclar.csv")
    for col in ['quant_score', 'score_diff', 'pct_flow', 'pct_hhi_mom']:
        df[col] = df[col].fillna(0).round(2)

    cols = ['ticker', 'quant_score', 'score_diff', 'pct_flow', 'pct_hhi_mom', 'rvol_ratio', 'change_%']
    names = ['Hisse', 'Skor', 'Fark', 'Yabancı %', 'Takas %', 'RVOL', 'Fiyat %']

    st.subheader("🏆 Kurumsal Onaylı Liderler")
    st.dataframe(df.head(20)[cols].rename(columns=dict(zip(cols, names))).style.background_gradient(subset=['Skor'], cmap='YlGn'), use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🚀 Atak Yapanlar")
        gainers = df[df['score_diff'] > 0.5].sort_values(by='score_diff', ascending=False).head(10)
        st.dataframe(gainers[cols].rename(columns=dict(zip(cols, names))), use_container_width=True)
    with c2:
        st.subheader("⚠️ Çıkış Radarı")
        losers = df[df['score_diff'] < -0.5].sort_values(by='score_diff', ascending=True).head(10)
        st.dataframe(losers[cols].rename(columns=dict(zip(cols, names))).style.background_gradient(subset=['Fark'], cmap='Reds_r'), use_container_width=True)
else:
    st.info("Veri bekleniyor...")
