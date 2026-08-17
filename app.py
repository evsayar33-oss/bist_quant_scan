import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="BIST Quant Terminal", layout="wide")
st.title("📊 BIST Nicel Mikroyapı & Çıkış Radarı")

if os.path.exists("sonuclar.csv") and os.path.exists("gecmis_veri.csv"):
    df = pd.read_csv("sonuclar.csv")
    df_gecmis = pd.read_csv("gecmis_veri.csv")
    
    # Sayıları yuvarla
    for col in ['quant_score', 'prev_quant_score', 'score_diff']:
        if col in df.columns: df[col] = df[col].round(2)

    # --- 1. SIDEBAR: HİSSE SORGULAMA ---
    st.sidebar.header("🔍 Hisse Takip / Sorgu")
    search_ticker = st.sidebar.text_input("Hisse Kodu Yaz (Örn: THYAO):").upper()
    
    if search_ticker:
        hisse_data = df[df['ticker'] == search_ticker]
        if not hisse_data.empty:
            score = hisse_data['quant_score'].iloc[0]
            diff = hisse_data['score_diff'].iloc[0]
            
            if score >= 70: status, s_col = "GÜÇLÜ TUT (BOĞA)", "green"
            elif score >= 50: status, s_col = "İZLE / KARARSIZ", "orange"
            else: status, s_col = "TEHLİKE / ÇIK", "red"

            st.sidebar.markdown(f"### {search_ticker}")
            st.sidebar.metric("Güncel Skor", score, f"{diff:+.2f}")
            st.sidebar.markdown(f"**Durum:** :{s_col}[{status}]")
            
            st.sidebar.write("Son 5 Tarama Geçmişi:")
            trend = df_gecmis[df_gecmis['ticker'] == search_ticker].tail(5)[['tarih', 'quant_score']]
            st.sidebar.table(trend)
        else:
            st.sidebar.warning("Hisse bulunamadı.")

    # --- 2. ANA TABLOLAR ---
    cols = ['ticker', 'quant_score', 'prev_quant_score', 'score_diff', 'rvol_ratio', 'pct_hhi', 'change_%']
    names = ['Hisse', 'Bugün', 'Dün', 'Fark', 'RVOL', 'HHI %', 'Fiyat %']

    st.subheader("🏆 Liderler (Top 20)")
    st.dataframe(df.head(20)[cols].rename(columns=dict(zip(cols, names))).style.background_gradient(subset=['Bugün'], cmap='RdYlGn'), use_container_width=True)

    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("🚀 Atak Yapanlar (Skor Artışı)")
        gainers = df[df['score_diff'] > 1.0].sort_values(by='score_diff', ascending=False).head(10)
        st.dataframe(gainers[cols].rename(columns=dict(zip(cols, names))).style.background_gradient(subset=['Fark'], cmap='Greens'), use_container_width=True)

    with col_b:
        st.subheader("⚠️ Çıkış Radarı (Güç Kaybedenler)")
        losers = df[df['score_diff'] < -1.0].sort_values(by='score_diff', ascending=True).head(10)
        st.dataframe(losers[cols].rename(columns=dict(zip(cols, names))).style.background_gradient(subset=['Fark'], cmap='Reds_r'), use_container_width=True)
    
    st.caption("💡 Çıkış Radarı: Skoru dünden bugüne en çok düşenleri gösterir. Skorun 50 altına inmesi teknik bozulma işaretidir.")
else:
    st.info("Veri bekleniyor. Lütfen GitHub Actions'ı bir kez manuel çalıştırın.")
