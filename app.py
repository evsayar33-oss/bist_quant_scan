import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="BIST Institutional Radar", layout="wide")
st.title("🛡️ BIST Kurumsal Akış & Gatekeeper")

if os.path.exists("sonuclar.csv"):
    df = pd.read_csv("sonuclar.csv")
    
    # SIDEBAR Sorgu
    st.sidebar.header("🔍 Hisse Detay")
    search = st.sidebar.text_input("Ticker:").upper()
    if search:
        h = df[df['ticker'] == search]
        if not h.empty:
            st.sidebar.metric("Quant Skor", h['quant_score'].iloc[0], f"{h['score_diff'].iloc[0]:+.2f}")
            st.sidebar.write(f"Hacim Gücü (RVOL): {h['rvol_ratio'].iloc[0]:.2f}x")
            st.sidebar.write(f"Kurumsal Onay: %{h['leading_score'].iloc[0]:.0f}")

    # TABLO
    st.subheader("🚀 Kurumsal Onaylı Liderler")
    cols = ['ticker', 'quant_score', 'leading_score', 'rvol_ratio', 'pct_hhi_mom', 'pct_flow', 'change_%']
    names = ['Hisse', 'Genel Skor', 'Kapı Puanı', 'RVOL', 'Takas Mom %', 'Yabancı Akış %', 'Fiyat %']
    
    st.dataframe(
        df.head(25)[cols].rename(columns=dict(zip(cols, names))).style.background_gradient(subset=['Genel Skor'], cmap='YlGn'),
        use_container_width=True
    )
    
    st.caption("💡 Sistem hem Hacim-Fiyat (Eski Mantık) hem de Takas-Yabancı Akışı (Yeni Mantık) onayı arar.")

else:
    st.info("Veri bekleniyor...")
