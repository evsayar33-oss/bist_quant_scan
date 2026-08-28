import streamlit as st
import pandas as pd
import numpy as np
import os

st.set_page_config(page_title="BIST Trend Initiation Terminal", layout="wide", page_icon="🎯")

st.title("🎯 BIST Orta Vadeli Trend Başlangıç & Sıkışma Terminali")
st.markdown("*Aşırı primlenmiş hisseleri eleyen, haftalık taban sıkışmasından (Squeeze) ilk kopan hisseleri tespit eden Quant Motoru.*")

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
    
    st.caption(f"🗓️ Son Tarama: **{son_tarih.strftime('%Y-%m-%d')}** | 📊 Taranan Hisse: **{len(df)}**")

    # Sayısal formatlamalar
    format_cols = ['quant_score', 'score_diff', 'close', 'sma50', 'sma200', 'rvol', 'perf_1m', 'change_%']
    for col in format_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).round(2)

    # --- SIDEBAR: HİSSE SORGULAMA ---
    st.sidebar.header("🔍 Hisse Trend Analizi")
    search_ticker = st.sidebar.text_input("Hisse Kodu (Örn: THYAO):").upper()
    
    if search_ticker:
        h_data = df[df['ticker'] == search_ticker]
        if not h_data.empty:
            score = float(h_data['quant_score'].iloc[0])
            diff = float(h_data['score_diff'].iloc[0])
            status = h_data['status_tag'].iloc[0]
            close_p = float(h_data['close'].iloc[0])
            p_1m = float(h_data['perf_1m'].iloc[0])
            
            st.sidebar.metric(f"{search_ticker} Trend Skoru", f"{score:.1f}", f"{diff:+.1f}")
            st.sidebar.write(f"**Durum:** {status}")
            st.sidebar.write(f"**Fiyat:** {close_p} TL | **1 Aylık Getiri:** %{p_1m:.1f}")
            
            st.sidebar.write("📈 Son 30 Günlük Skor Trendi:")
            trend = df_gecmis[df_gecmis['ticker'] == search_ticker][['tarih', 'quant_score']].sort_values('tarih')
            if not trend.empty:
                trend.set_index('tarih', inplace=True)
                st.sidebar.line_chart(trend['quant_score'])
        else:
            st.sidebar.warning("Hisse bulunamadı veya likidite filtresine takıldı.")

    # --- 1. ANA TABLO: TREND BAŞLANGICI VE SIKIŞMADAN KOPANLAR ---
    st.subheader("🚀 Erken Aşama Trend Başlangıçları (Kırmızı Oklar)")
    st.markdown("*SMA50 tabanına yakın, volatilitesi sıkışmış ve ilk hacimli kırılımını yapan adaylar.*")
    
    # 50 puan ve üstü alan gerçek fırsatlar
    top_candidates = df[df['quant_score'] >= 45.0].sort_values(by='quant_score', ascending=False)
    
    display_cols = ['ticker', 'quant_score', 'score_diff', 'status_tag', 'close', 'sma50', 'rvol', 'perf_1m', 'change_%']
    display_cols = [c for c in display_cols if c in df.columns]
    
    col_names = {
        'ticker': 'Hisse',
        'quant_score': 'Trend Skoru',
        'score_diff': 'İvme Farkı',
        'status_tag': 'Formasyon Durumu',
        'close': 'Fiyat (TL)',
        'sma50': '50 Günlük Ort.',
        'rvol': 'RVOL (Hacim Katı)',
        'perf_1m': '1 Aylık Değişim %',
        'change_%': 'Günlük %'
    }
    
    if not top_candidates.empty:
        st.dataframe(
            top_candidates[display_cols].rename(columns=col_names).style.background_gradient(subset=['Trend Skoru'], cmap='Greens').format({
                'Trend Skoru': '{:.1f}',
                'İvme Farkı': '{:+.1f}',
                'Fiyat (TL)': '{:.2f}',
                '50 Günlük Ort.': '{:.2f}',
                'RVOL (Hacim Katı)': '{:.1f}x',
                '1 Aylık Değişim %': '%{:.1f}',
                'Günlük %': '%{:.1f}'
            }),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("ℹ️ Bugün yeni bir taban sıkışma kırılımı gerçekleşmedi. Sistem tepedeki hisseleri bilerek elemektedir.")

    st.divider()

    # --- 2. DİSKALİFİYE EDİLENLER: AŞIRI ŞİŞMİŞ TEPEDEKİ HİSSELER ---
    st.subheader("🚫 Aşırı Primli / Tepe Formasyonları (Uzak Durulması Gerekenler)")
    st.markdown("*50 günlük ortalamasından aşırı uzaklaşmış veya son 1 ayda çok sert yükselmiş hisseler.*")
    
    overextended = df[df['status_tag'].str.contains('AŞIRI ŞİŞMİŞ', na=False)].sort_values(by='perf_1m', ascending=False).head(10)
    if not overextended.empty:
        st.dataframe(
            overextended[display_cols].rename(columns=col_names).style.background_gradient(subset=['1 Aylık Değişim %'], cmap='Reds').format({
                'Trend Skoru': '{:.1f}',
                'İvme Farkı': '{:+.1f}',
                'Fiyat (TL)': '{:.2f}',
                '50 Günlük Ort.': '{:.2f}',
                'RVOL (Hacim Katı)': '{:.1f}x',
                '1 Aylık Değişim %': '%{:.1f}',
                'Günlük %': '%{:.1f}'
            }),
            use_container_width=True,
            hide_index=True
        )

else:
    st.info("🕒 Sistem başlatılıyor... Lütfen GitHub Actions üzerinden 'Run workflow' yapınız.")
