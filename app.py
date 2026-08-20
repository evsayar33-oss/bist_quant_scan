import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="BIST Quant Terminal", layout="wide")
st.title("📊 BIST Nicel Radar & Çıkış Sistemi")

if os.path.exists("sonuclar.csv") and os.path.exists("gecmis_veri.csv"):
    df = pd.read_csv("sonuclar.csv")
    df_gecmis = pd.read_csv("gecmis_veri.csv")
    
    for col in ['quant_score', 'prev_quant_score', 'score_diff']:
        if col in df.columns: df[col] = df[col].round(2)

    # --- SIDEBAR: HİSSE SORGULAMA ---
    st.sidebar.header("🔍 Hisse Sorgu")
    search_ticker = st.sidebar.text_input("Hisse Kodu (Örn: THYAO):").upper()
    if search_ticker:
        h_data = df[df['ticker'] == search_ticker]
        if not h_data.empty:
            score = h_data['quant_score'].iloc[0]
            diff = h_data['score_diff'].iloc[0]
            status = "🚀 TUT" if score > 70 else ("🛑 RİSK" if score < 45 else "NÖTR")
            st.sidebar.metric(f"{search_ticker} Skor", score, f"{diff:+.2f}")
            st.sidebar.write(f"**Durum:** {status}")
            
            st.sidebar.write("Son 5 Günlük Trend:")
            trend = df_gecmis[df_gecmis['ticker'] == search_ticker].tail(5)[['tarih', 'quant_score']]
            st.sidebar.table(trend)

    # --- TABLOLAR ---
    cols = ['ticker', 'quant_score', 'score_diff', 'rvol_ratio', 'pct_hhi', 'change_%']
    names = ['Hisse', 'Skor', 'Fark', 'RVOL', 'HHI Dilimi', 'Fiyat %']

    st.subheader("🏆 Günün Nicel Liderleri (Top 20)")
    st.dataframe(df.head(20)[cols].rename(columns=dict(zip(cols, names))).style.background_gradient(subset=['Skor'], cmap='RdYlGn'), use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🔥 Atak Yapanlar")
        gainers = df[df['score_diff'] > 1.0].sort_values(by='score_diff', ascending=False).head(10)
        st.dataframe(gainers[cols].rename(columns=dict(zip(cols, names))), use_container_width=True)

    with col2:
        st.subheader("⚠️ Çıkış Radarı")
        losers = df[df['score_diff'] < -1.0].sort_values(by='score_diff', ascending=True).head(10)
        st.dataframe(losers[cols].rename(columns=dict(zip(cols, names))).style.background_gradient(subset=['Fark'], cmap='Reds_r'), use_container_width=True)
else:
    st.info("Veri bekleniyor...")
