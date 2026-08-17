import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="BIST Quant Radar", layout="wide")
st.title("📊 BIST Nicel Mikroyapı Radarı")

# Dosya kontrolü
if os.path.exists("sonuclar.csv"):
    try:
        # Veriyi oku
        df = pd.read_csv("sonuclar.csv")
        
        # Metrikler
        col1, col2 = st.columns(2)
        col1.metric("Taranan Toplam Hisse", len(df))
        col2.info("Veriler her akşam 17:30'da otomatik güncellenir.")

        st.subheader("🚀 En Yüksek Quant Skorlu Hisseler")
        
        # Görüntülenecek sütunlar
        cols = ['ticker', 'quant_score', 'rvol_ratio', 'pct_hhi', 'change_%', 'close', 'gecmis_yetersiz']
        disp_df = df[cols].copy()
        
        # Sütun isimlerini Türkçeleştir
        disp_df.columns = ['Hisse', 'Skor', 'RVOL', 'HHI %', 'Değişim %', 'Fiyat', 'Yeni Kayıt']

        # Tabloyu renklendirerek göster (Matplotlib hatasını bu blok çözer)
        st.dataframe(
            disp_df.style.background_gradient(subset=['Skor'], cmap='RdYlGn'),
            use_container_width=True,
            height=600
        )
        
        st.caption("💡 Skor: 100'e yakınsa sinyal güçlüdür. RVOL: 1.0'dan büyükse hacim artışı vardır.")

    except Exception as e:
        st.error(f"Veri okunurken bir hata oluştu: {e}")
else:
    st.warning("Henüz tarama verisi oluşmadı. GitHub Actions işleminin bitmesini bekleyin.")
