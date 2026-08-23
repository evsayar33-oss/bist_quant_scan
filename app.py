import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="BIST Institutional Radar", layout="wide")
st.title("🛡️ BIST Kurumsal Akış & Gatekeeper")

if os.path.exists("sonuclar.csv"):
    try:
        df = pd.read_csv("sonuclar.csv")
        
        # SÜTUN KONTROLÜ: Eğer yeni sütunlar yoksa hata verme, boş göster
        required_cols = ['ticker', 'quant_score', 'leading_score', 'pct_flow', 'pct_hhi_mom', 'change_%']
        for col in required_cols:
            if col not in df.columns:
                df[col] = 0.0 # Henüz taranmamış veriyi 0 kabul et

        # Metrikler
        st.sidebar.header("🔍 Hisse Detay")
        search = st.sidebar.text_input("Hisse Sorgu:").upper()
        if search:
            h = df[df['ticker'] == search]
            if not h.empty:
                st.sidebar.metric("Quant Skor", f"{h['quant_score'].iloc[0]:.2f}")
        
        # Tablo Gösterimi
        st.subheader("🏆 Kurumsal Onaylı Liderler")
        mapping = {
            'ticker': 'Hisse', 'quant_score': 'Skor', 'leading_score': 'Kapı Puanı',
            'pct_flow': 'Yabancı Akış %', 'pct_hhi_mom': 'Takas Güç %', 'change_%': 'Fiyat %'
        }
        
        disp_df = df[required_cols].rename(columns=mapping)
        st.dataframe(
            disp_df.style.background_gradient(subset=['Skor'], cmap='YlGn'),
            use_container_width=True
        )
        st.caption("💡 Not: Eğer değerler 0 görünüyorsa, yeni kurumsal taramanın (Actions) bitmesini bekleyin.")

    except Exception as e:
        st.error(f"Veri işleme hatası: {e}")
else:
    st.info("Veri bekleniyor... GitHub Actions çalışınca tablo dolacaktır.")
