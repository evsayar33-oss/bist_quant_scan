import streamlit as st
import pandas as pd
import os
 
st.set_page_config(page_title="BIST Quant Radar", layout="centered")
st.title("BIST Nicel Takas & Mikroyapi Radari")
 
if os.path.exists("sonuclar.csv"):
    df = pd.read_csv("sonuclar.csv")
 
    st.metric(label="Taranan Toplam Hisse", value=len(df))
      st.subheader("En Yuksek Quant Skorlu Hisseler")
    st.dataframe(
        df[[
            'ticker', 'quant_score', 'rvol_ratio', 'pct_hhi',
            'change_%', 'close', 'gecmis_yetersiz'
        ]],
        use_container_width=True
    )
    st.caption(
        "rvol_ratio: hissenin kendi son 20 gunluk ortalama hacmine gore bugunku hacim orani. "
        "gecmis_yetersiz = True: bu hisse icin henuz 5 gunden az kayit var, RVOL evren "
        "medyaniyla dolduruldu (sistem yeni kuruldugunda ilk gunlerde beklenen bir durum)."
    )
else:
    st.info("Henuz taranmis veri bulunmuyor. GitHub Actions calismasini bekleyin.")
