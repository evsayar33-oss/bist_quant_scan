import streamlit as st
import pandas as pd
import numpy as np
import os

st.set_page_config(page_title="BIST Quant Terminal", layout="wide", page_icon="🛡️")

st.title("🛡️ BIST Alpha Overlay & Kurumsal Akış Terminali")

def load_data():
    if os.path.exists("gecmis_veri.csv"):
        try:
            df = pd.read_csv("gecmis_veri.csv")
            if 'tarih' in df.columns:
                df['tarih'] = pd.to_datetime(df['tarih'])
            return df
        except Exception as e:
            st.error(f"Dosya okuma hatası: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

df_gecmis = load_data()

if not df_gecmis.empty:
    son_tarih = df_gecmis['tarih'].max()
    df = df_gecmis[df_gecmis['tarih'] == son_tarih].copy()
    
    st.caption(f"🗓️ Son Güncelleme: **{son_tarih.strftime('%Y-%m-%d')}** | 📊 Taranan Hisse: **{len(df)}**")

    # Sayısal formatlamalar (2 basamaklı temiz görünüm)
    format_cols = ['quant_score', 'score_diff', 'foreign_ratio', 'hhi_score', 'change_%']
    for col in format_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).round(2)

    # --- YAN PANEL: HİSSE SORGULAMA ---
    st.sidebar.header("🔍 Kurumsal Hisse Sorgu")
    search_ticker = st.sidebar.text_input("Hisse Kodu (Örn: THYAO):").upper()
    
    if search_ticker:
        h_data = df[df['ticker'] == search_ticker]
        if not h_data.empty:
            score = float(h_data['quant_score'].iloc[0])
            diff = float(h_data['score_diff'].iloc[0])
            
            status = "🚀 GÜÇLÜ (ALIM/TOPLAMA)" if score > 30 else ("⚠️ RİSKLİ (DAĞITIM)" if score < 15 else "NÖTR")
            
            st.sidebar.metric(f"{search_ticker} Alpha Skoru", f"{score:.2f}", f"{diff:+.2f}")
            st.sidebar.write(f"**Piyasa Rejimi:** {status}")
            
            st.sidebar.write("📈 Momentum Trendi:")
            trend = df_gecmis[df_gecmis['ticker'] == search_ticker][['tarih', 'quant_score']].sort_values('tarih')
            if not trend.empty:
                trend.set_index('tarih', inplace=True)
                st.sidebar.line_chart(trend['quant_score'])
        else:
            st.sidebar.warning("Hisse veritabanında bulunamadı.")

    # --- ANA TABLOLAR ---
    display_cols = ['ticker', 'quant_score', 'score_diff', 'foreign_ratio', 'hhi_score', 'volume', 'change_%']
    display_cols = [c for c in display_cols if c in df.columns]
    
    col_names = {
        'ticker': 'Hisse',
        'quant_score': 'Alpha Skor',
        'score_diff': 'Fark (1G)',
        'foreign_ratio': 'Yabancı Takas %',
        'hhi_score': 'HHI Konsantrasyon',
        'volume': 'Hacim',
        'change_%': 'Fiyat %'
    }
    
    df_display = df[display_cols].rename(columns=col_names)

    # 1. LİDERLER TABLOSU
    st.subheader("🏆 Kurumsal Onaylı Liderler (Top 20)")
    st.markdown("*Akıllı Para (Smart Money) onayı almış, gün sonu mikro-yapısı (CLV) güçlü ve hacmi stabil hisseler.*")
    top_20 = df_display.sort_values(by='Alpha Skor', ascending=False).head(20)
    st.dataframe(
        top_20.style.background_gradient(subset=['Alpha Skor'], cmap='Greens').format({
            'Alpha Skor': '{:.2f}',
            'Fark (1G)': '{:+.2f}',
            'Yabancı Takas %': '{:.2f}',
            'HHI Konsantrasyon': '{:.2f}',
            'Fiyat %': '%{:.2f}'
        }), 
        use_container_width=True, 
        hide_index=True
    )

    st.divider()

    # 2. MOMENTUM VE ÇIKIŞ
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🚀 Atak Yapanlar (Momentum)")
        gainers = df_display[df_display['Fark (1G)'] > 0].sort_values(by='Fark (1G)', ascending=False).head(10)
        st.dataframe(
            gainers.style.background_gradient(subset=['Fark (1G)'], cmap='Blues').format({
                'Alpha Skor': '{:.2f}',
                'Fark (1G)': '{:+.2f}',
                'Yabancı Takas %': '{:.2f}',
                'HHI Konsantrasyon': '{:.2f}',
                'Fiyat %': '%{:.2f}'
            }), 
            use_container_width=True, 
            hide_index=True
        )
        
    with c2:
        st.subheader("⚠️ Çıkış Radarı (Dağıtım)")
        losers = df_display[df_display['Fark (1G)'] < 0].sort_values(by='Fark (1G)', ascending=True).head(10)
        st.dataframe(
            losers.style.background_gradient(subset=['Fark (1G)'], cmap='Reds_r').format({
                'Alpha Skor': '{:.2f}',
                'Fark (1G)': '{:+.2f}',
                'Yabancı Takas %': '{:.2f}',
                'HHI Konsantrasyon': '{:.2f}',
                'Fiyat %': '%{:.2f}'
            }), 
            use_container_width=True, 
            hide_index=True
        )

else:
    st.info("🕒 Veritabanı oluşturuluyor... Lütfen Actions üzerinden Run workflow yapınız.")
