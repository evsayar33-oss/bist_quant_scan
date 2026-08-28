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
    # Sadece trend başlangıç puanı 50 ve üzeri olan gerçek adayları al
    valid_candidates = df_scored[df_scored['quant_score'] >= 50.0].head(10)
    
    msg = f"🎯 <b>BIST ORTA VADELİ TREND BAŞLANGIÇ RAPORU</b>\n"
    msg += f"🗓 <i>Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M')}</i>\n"
    msg += "<i>(Aşırı şişmiş hisseler elenmiş, tabandan ilk kopanlar seçilmiştir)</i>\n\n"
    
    if valid_candidates.empty:
        msg += "⚠️ <i>Bugün kriterlere uyan yeni bir taban sıkışma kırılımı bulunamadı.</i>"
        return msg

    msg += "🚀 <b>ERKEN TREND KIRILIM ADAYLARI (Top 10)</b>\n"
    for idx, row in valid_candidates.iterrows():
        fark = f"(+{row['score_diff']:.1f})" if row.get('score_diff', 0) > 0 else f"({row.get('score_diff', 0):.1f})"
        msg += f"• <b>{row['ticker']}</b> : Trend Skoru: <b>{row['quant_score']:.1f}</b> {fark} | Fiyat: {row['close']} TL (1A: %{row['perf_1m']:.1f})\n"
        msg += f"  └ <i>Durum: {row['status_tag']} | RVOL: {row['rvol']:.1f}x</i>\n"
        
    return msg

def main():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] === Trend Initiation Scanner Başlıyor ===")
    
    df_current = fetch_all_data()
    if df_current.empty:
        print("Hata: Piyasa verisi alınamadı.")
        return

    df_gecmis = gecmis_veriyi_yukle()
    df_scored = calculate_quant_scores(df_current, df_gecmis)
    
    if df_scored.empty:
        print("Puanlanmış veri boş döndü.")
        return

    # Veritabanını güncelle
    if not df_gecmis.empty:
        bugun = pd.Timestamp.now().normalize()
        df_gecmis = df_gecmis[df_gecmis['tarih'] != bugun]
        df_yeni_gecmis = pd.concat([df_gecmis, df_scored], ignore_index=True)
    else:
        df_yeni_gecmis = df_scored

    df_yeni_gecmis['tarih'] = pd.to_datetime(df_yeni_gecmis['tarih'])
    limit_tarih = pd.Timestamp.now().normalize() - pd.Timedelta(days=30)
    df_yeni_gecmis = df_yeni_gecmis[df_yeni_gecmis['tarih'] >= limit_tarih]
    
    df_yeni_gecmis.to_csv(GECMIS_DOSYA, index=False)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Başarılı! {GECMIS_DOSYA} kaydedildi.")

    # Telegram Raporu Gönder
    telegram_msg = format_quant_report(df_scored)
    send_telegram_message(telegram_msg)

if __name__ == "__main__":
    main()
