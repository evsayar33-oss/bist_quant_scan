import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="BIST Quant Radar", layout="wide")
st.title("📊 BIST Nicel Mikroyapı Terminali")

if os.path.exists("sonuclar.csv"):
    df = pd.read_csv("sonuclar.csv")
    
    # Yardımcı kolonlar ve isimler
    cols = ['ticker', 'quant_score', 'prev_quant_score', 'score_diff', 'rvol_ratio', 'pct_hhi', 'change_%']
    names = ['Hisse', 'Skor', 'Dünkü Skor', 'Skor Farkı', 'RVOL', 'HHI Dilimi', 'Fiyat %']

    # --- TABLO 1: GENEL SIRALAMA ---
    st.subheader("🏆 Genel Nicel Liderler (Top 20)")
    t1 = df.head(20)[cols].copy()
    t1.columns = names
    st.dataframe(t1.style.background_gradient(subset=['Skor'], cmap='RdYlGn'), use_container_width=True)

    col_a, col_b = st.columns(2)

    # --- TABLO 2: EN ÇOK SKOR KAZANANLAR ---
    with col_a:
        st.subheader("🚀 Atak Yapanlar (Skor Artışı)")
        t2 = df.sort_values(by='score_diff', ascending=False).head(10)[cols].copy()
        t2.columns = names
        st.dataframe(t2.style.background_gradient(subset=['Skor Farkı'], cmap='Greens'), use_container_width=True)

    # --- TABLO 3: EN ÇOK SKOR KAYBEDENLER ---
    with col_b:
        st.subheader("⚠️ Güç Kaybedenler (Skor Düşüşü)")
        t3 = df.sort_values(by='score_diff', ascending=True).head(10)[cols].copy()
        t3.columns = names
        st.dataframe(t3.style.background_gradient(subset=['Skor Farkı'], cmap='Reds_r'), use_container_width=True)

    st.caption("💡 Atak Yapanlar: Bugün hacim, fiyat veya takas tarafında yeni bir hareket başlatanlar.")
else:
    st.info("Tarama verisi bekleniyor...")
