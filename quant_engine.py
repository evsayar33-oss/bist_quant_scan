import numpy as np
import pandas as pd
import os

GECMIS_DOSYA = "gecmis_veri.csv"
RVOL_PENCERE = 20
MIN_GECMIS_GUN = 5

def gecmis_veriyi_yukle():
    if os.path.exists(GECMIS_DOSYA):
        try:
            return pd.read_csv(GECMIS_DOSYA, parse_dates=['tarih'])
        except:
            return pd.DataFrame(columns=['tarih', 'ticker', 'close', 'volume', 'change_%', 'hhi_score'])
    return pd.DataFrame(columns=['tarih', 'ticker', 'close', 'volume', 'change_%', 'hhi_score'])

def calculate_hhi(takas_shares):
    """Saklama yoğunlaşmasını ölçer (Payda kontrolü eklendi)."""
    if not takas_shares or sum(takas_shares) == 0:
        return 0.0
    shares = np.array(takas_shares)
    # Oranları normalize et (toplamı 100 yapacak şekilde)
    normalized_shares = (shares / shares.sum()) * 100
    return float(np.sum(normalized_shares ** 2))

def hisse_bazli_rvol_hesapla(df_bugun, df_gecmis):
    rvol_oranlari = []
    for _, row in df_bugun.iterrows():
        ticker = row['ticker']
        # Sadece o hissenin geçmişine bak
        gecmis_hacim = df_gecmis[df_gecmis['ticker'] == ticker]['volume'].tail(RVOL_PENCERE)
        
        if len(gecmis_hacim) >= MIN_GECMIS_GUN:
            ort_hacim = gecmis_hacim.mean()
            rvol = row['volume'] / ort_hacim if ort_hacim > 0 else 1.0
        else:
            rvol = np.nan
        rvol_oranlari.append(rvol)
    
    df_bugun['rvol_ratio'] = rvol_oranlari
    return df_bugun

def calculate_quant_scores(df, df_gecmis):
    if df.empty: return df

    # 1) RVOL Hesapla
    df = hisse_bazli_rvol_hesapla(df, df_gecmis)
    
    # 2) Eksik RVOL'leri medyanla doldur (Yeni hisseler için)
    yeterli_gecmis = df['rvol_ratio'].notna()
    medyan_rvol = df.loc[yeterli_gecmis, 'rvol_ratio'].median() if yeterli_gecmis.any() else 1.0
    df['rvol_ratio'] = df['rvol_ratio'].fillna(medyan_rvol)
    df['gecmis_yetersiz'] = ~yeterli_gecmis

    # 3) Percentile Rank (Yüzdelik Dilimleme)
    df['pct_rvol'] = df['rvol_ratio'].rank(pct=True) * 100
    df['pct_change'] = df['change_%'].rank(pct=True) * 100
    df['pct_hhi'] = df['hhi_score'].rank(pct=True) * 100

    # 4) Toplam Skor
    df['quant_score'] = (df['pct_rvol'] * 0.40) + (df['pct_change'] * 0.30) + (df['pct_hhi'] * 0.30)
    
    return df.sort_values(by='quant_score', ascending=False).reset_index(drop=True)
