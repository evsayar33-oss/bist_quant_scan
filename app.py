import streamlit as st
import pandas as pd
import os

# Sayfa Ayarları (Kurumsal Görünüm)
st.set_page_config(page_title="BIST Quant Terminal", layout="wide", page_icon="🛡️")

st.title("🛡️ BIST Alpha Overlay & Kurumsal Akış Terminali")

# ÖNBELLEK YÖNETİMİ: 5 dakikada bir (300 sn) veriyi zorla yeniler. Cache takılmalarını engeller.
@st.cache_data(ttl=300)
def load_data():
    # Artık 'sonuclar.csv' yok, tüm veriler 'gecmis_veri.csv' içinden çekilir.
    if os.path.exists("gecmis_veri.csv"):
        try:
            df = pd.read_csv("gecmis_veri.csv")
            df['tarih'] = pd.to_datetime(df['tarih'])
            return df
        except Exception as e:
            st.error(f"Dosya okuma hatası: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

# Veriyi Çek
df_gecmis = load_data()

if not df_gecmis.empty:
    # 1. EN GÜNCEL GÜNÜ BUL (Ana Tablolar için)
    son_tarih = df_gecmis['tarih'].max()
    df = df_gecmis[df_gecmis['tarih'] == son_tarih].copy()
    
    st.caption(f"🗓️ Son Güncelleme: **{son_tarih.strftime('%Y-%m-%d')}** | 📊 Taranan Hisse: **{len(df)}**")
    
    # 2. SAYILARI YUVARLA VE TEMİZLE
    # Eski iptal olan kolonları sildik, yeni Quant motorunun kolonlarını kullanıyoruz
    format_cols = ['quant_score', 'score_diff', 'foreign_ratio', 'hhi_score', 'change_%']
    for col in format_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).round(2)

    # --- YAN PANEL (SIDEBAR): HİSSE SORGULAMA ---
    st.sidebar.header("🔍 Kurumsal Hisse Sorgu")
    search_ticker = st.sidebar.text_input("Hisse Kodu (Örn: THYAO):").upper()
    
    if search_ticker:
        h_data = df[df['ticker'] == search_ticker]
        if not h_data.empty:
            score = h_data['quant_score'].iloc[0]
            diff = h_data['score_diff'].iloc[0]
            
            # Dinamik Rejim Filtresi
            status = "🚀 GÜÇLÜ (ALIM/TOPLAMA)" if score > 50 else ("⚠️ RİSKLİ (DAĞITIM)" if score < 30 else "NÖTR")
            
            st.sidebar.metric(f"{search_ticker} Alpha Skoru", f"{score}", f"{diff:+.2f}")
            st.sidebar.write(f"**Piyasa Rejimi:** {status}")
            
            # Trend Grafiği (Tablo yerine görsel Line Chart)
            st.sidebar.write("📈 Son 30 Günlük Momentum Trendi:")
            trend = df_gecmis[df_gecmis['ticker'] == search_ticker][['tarih', 'quant_score']].sort_values('tarih')
            if not trend.empty:
                trend.set_index('tarih', inplace=True)
                st.sidebar.line_chart(trend['quant_score'])
        else:
            st.sidebar.warning("Hisse bulunamadı. (Hacim barajına takılmış olabilir).")

    # --- ANA TABLOLAR İÇİN SÜTUN SEÇİMİ VE İSİMLENDİRME ---
    display_cols = ['ticker', 'quant_score', 'score_diff', 'foreign_ratio', 'hhi_score', 'volume', 'change_%']
    # Olası eksik kolon hatalarını engelle
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

    # --- 1. LİDERLER TABLOSU ---
    st.subheader("🏆 Kurumsal Onaylı Liderler (Top 20)")
    st.markdown("*Akıllı Para (Smart Money) onayı almış, gün sonu mikro-yapısı (CLV) güçlü ve hacmi stabil hisseler.*")
    top_20 = df_display.sort_values(by='Alpha Skor', ascending=False).head(20)
    st.dataframe(
        top_20.style.background_gradient(subset=['Alpha Skor'], cmap='Greens'), 
        use_container_width=True, 
        hide_index=True
    )

    st.divider()

    # --- 2. MOMENTUM VE ÇIKIŞ RADARI ---
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🚀 Atak Yapanlar (Momentum)")
        st.markdown("*Düne göre Alpha skorunu en çok artıran hisseler.*")
        gainers = df_display[df_display['Fark (1G)'] > 1.0].sort_values(by='Fark (1G)', ascending=False).head(10)
        st.dataframe(
            gainers.style.background_gradient(subset=['Fark (1G)'], cmap='Blues'), 
            use_container_width=True, 
            hide_index=True
        )
        
    with c2:
        st.subheader("⚠️ Çıkış Radarı (Dağıtım)")
        st.markdown("*Kurumsal çıkış yiyen veya trend tükenişi (Exhaustion) yaşayanlar.*")
        losers = df_display[df_display['Fark (1G)'] < -1.0].sort_values(by='Fark (1G)', ascending=True).head(10)
        st.dataframe(
            losers.style.background_gradient(subset=['Fark (1G)'], cmap='Reds_r'), 
            use_container_width=True, 
            hide_index=True
        )

else:
    st.info("🕒 Veri bekleniyor... GitHub Actions motoru çalıştığında burası otomatik dolacaktır.")
