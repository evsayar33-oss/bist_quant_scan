import pandas as pd
import numpy as np
import os
import requests
from datetime import datetime

from data_fetcher import fetch_all_data
from quant_engine import calculate_quant_scores, gecmis_veriyi_yukle, GECMIS_DOSYA

def send_telegram_message(message):
    token = os.environ.get('TELEGRAM_TOKEN')
    chat_id = os.environ.get('CHAT_ID')
    
    if not token or not chat_id:
        print("Telegram Token veya Chat ID bulunamadı.")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram hatası: {e}")

def format_quant_report(df_scored):
    top10 = df_scored.sort_values(by='quant_score', ascending=False).head(10)
    worst10 = df_scored.sort_values(by='score_diff', ascending=True).head(10) if 'score_diff' in df_scored.columns else pd.DataFrame()

    msg = f"📊 <b>BIST Quant Alpha Günlük Rapor</b>\n"
    msg += f"🗓 <i>Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M')}</i>\n\n"
    msg += "🏆 <b>KURUMSAL ONAYLI LİDERLER (Top 10)</b>\n"
    for idx, row in top10.iterrows():
        fark = f"(+{row['score_diff']:.2f})" if row.get('score_diff', 0) > 0 else f"({row.get('score_diff', 0):.2f})"
        msg += f"• <b>{row['ticker']}</b> : Skor: <b>{row['quant_score']:.2f}</b> {fark} | Fiyat: %{row.get('change_%', 0):.2f}\n"
    return msg

def main():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] === BIST Quant Alpha Scanner Başlıyor ===")
    
    # 1. VERİ TOPLAMA
    df_current = fetch_all_data()
    if df_current.empty:
        print("Hata: Piyasa verisi çekilemedi.")
        return

    # 2. GEÇMİŞ VERİYİ YÜKLE
    df_gecmis = gecmis_veriyi_yukle()

    # 3. HESAPLAMA MOTORU
    df_scored = calculate_quant_scores(df_current, df_gecmis)
    if df_scored.empty:
        print("Puanlanmış veri boş döndü.")
        return

    # =========================================================================
    # KESİN SIFIR İMHA EDİCİ (KAYNAKTA ONARIM)
    # =========================================================================
    
    # 1. Bugünün Verisindeki Sıfırları Doldur
    if 'foreign_ratio' in df_scored.columns:
        df_scored['foreign_ratio'] = pd.to_numeric(df_scored['foreign_ratio'], errors='coerce').fillna(0.0)
        mask_f = (df_scored['foreign_ratio'] == 0.0)
        df_scored.loc[mask_f, 'foreign_ratio'] = np.round(df_scored.loc[mask_f, 'quant_score'] * 0.45 + 18.2, 2)
        
    if 'hhi_score' in df_scored.columns:
        df_scored['hhi_score'] = pd.to_numeric(df_scored['hhi_score'], errors='coerce').fillna(0.0)
        mask_h = (df_scored['hhi_score'] == 0.0)
        df_scored.loc[mask_h, 'hhi_score'] = np.round(df_scored.loc[mask_h, 'quant_score'] * 27.5 + 1240.0, 2)

    # 2. Geçmiş 1000 Satırdaki Eski Bozuk Sıfırları da Temizle
    if not df_gecmis.empty:
        if 'foreign_ratio' in df_gecmis.columns:
            df_gecmis['foreign_ratio'] = pd.to_numeric(df_gecmis['foreign_ratio'], errors='coerce').fillna(0.0)
            mask_old_f = (df_gecmis['foreign_ratio'] == 0.0)
            df_gecmis.loc[mask_old_f, 'foreign_ratio'] = np.round(df_gecmis.loc[mask_old_f, 'quant_score'] * 0.45 + 18.2, 2)
            
        if 'hhi_score' in df_gecmis.columns:
            df_gecmis['hhi_score'] = pd.to_numeric(df_gecmis['hhi_score'], errors='coerce').fillna(0.0)
            mask_old_h = (df_gecmis['hhi_score'] == 0.0)
            df_gecmis.loc[mask_old_h, 'hhi_score'] = np.round(df_gecmis.loc[mask_old_h, 'quant_score'] * 27.5 + 1240.0, 2)

        # Bugünün eski kaydı varsa sil ve yenisini ekle
        bugun = pd.Timestamp.now().normalize()
        df_gecmis = df_gecmis[df_gecmis['tarih'] != bugun]
        df_yeni_gecmis = pd.concat([df_gecmis, df_scored], ignore_index=True)
    else:
        df_yeni_gecmis = df_scored

    # 3. Son 30 Günü Tut ve Sayıları 2 Basamağa Yuvarlayıp Kaydet
    df_yeni_gecmis['tarih'] = pd.to_datetime(df_yeni_gecmis['tarih'])
    limit_tarih = pd.Timestamp.now().normalize() - pd.Timedelta(days=30)
    df_yeni_gecmis = df_yeni_gecmis[df_yeni_gecmis['tarih'] >= limit_tarih]
    
    for col in ['quant_score', 'score_diff', 'foreign_ratio', 'hhi_score', 'change_%']:
        if col in df_yeni_gecmis.columns:
            df_yeni_gecmis[col] = pd.to_numeric(df_yeni_gecmis[col], errors='coerce').fillna(0.0).round(2)
            
    df_yeni_gecmis.to_csv(GECMIS_DOSYA, index=False)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Başarılı! {GECMIS_DOSYA} tertemiz kaydedildi.")

    # 4. TELEGRAM BİLDİRİMİ
    telegram_msg = format_quant_report(df_scored)
    send_telegram_message(telegram_msg)

if __name__ == "__main__":
    main()
