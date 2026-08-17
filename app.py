import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="BIST Quant Radar", layout="wide")
st.title("📊 BIST Nicel Mikroyapı Radarı")

if os.path.exists("sonuclar.csv"):
    df = pd.read_csv("sonuclar.csv")
    
    col1, col2 = st.columns(2)
    col1.metric("Taranan Hisse", len(df))
    col2.info("Veriler her akşam 18:45'te güncellenir.")

    st.subheader("🚀 En Yüksek Skorlu Hisseler")
    # Görsel düzenleme
    disp_df = df[['ticker', 'quant_score', 'rvol_ratio', 'pct_hhi', 'change_%', 'close', 'gecmis_yetersiz']].copy()
    disp_df.columns = ['Hisse', 'Quant Skor', 'RVOL Oranı', 'HHI Dilimi', 'Fiyat Değişim', 'Kapanış', 'Yetersiz Geçmiş']
    
    st.dataframe(disp_df.style.background_gradient(subset=['Quant Skor'], cmap='RdYlGn'), use_container_width=True)
else:
    st.warning("Veri bulunamadı. Lütfen taramanın tamamlanmasını bekleyin.")
