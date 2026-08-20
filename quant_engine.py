import numpy as np
import pandas as pd
import os

GECMIS_DOSYA = "gecmis_veri.csv"
RVOL_PENCERE = 20
MIN_GECMIS_GUN = 5

def gecmis_veriyi_yukle():
    if os.path.exists(GECMIS_DOSYA):
        try:
            df = pd.read_csv(GECMIS_DOSYA)
            df['tarih'] = pd.to_datetime(df['tarih'])
            return df
        except: return pd.DataFrame()
    return pd.DataFrame()

def calculate_hhi(takas_shares):
    if not takas_shares or sum(takas_shares) == 0: return 0.0
    shares = np.array(takas_shares)
    normalized = (shares / shares.sum()) * 100
    return float(np.sum(normalized ** 2))

def calculate_quant_scores(df, df_gecmis):
    if df.empty: return df

    # 1. RVOL Hesapla
    rvol_list = []
    for _, row in df.iterrows():
        gecmis_v = df_gecmis[df_gecmis['ticker'] == row['ticker']]['volume'].tail(RVOL_PENCERE) if not df_gecmis.empty else []
        rvol_list.append(row['volume'] / gecmis_v.mean() if len(gecmis_v) >= MIN_GECMIS_GUN else 1.0)
    df['rvol_ratio'] = rvol_list
    
    # 2. ADAPTIF SKORLAMA (ABD Mantigi: Her sey Percentile Rank)
    df['pct_rvol'] = df['rvol_ratio'].rank(pct=True) * 100
    df['pct_change'] = df['change_%'].rank(pct=True) * 100
    df['pct_hhi'] = df['hhi_score'].rank(pct=True) * 100
    
    # Final Skor (Agirliklar: %40 Hacim, %30 Takas, %30 Fiyat)
    df['quant_score'] = (df['pct_rvol'] * 0.40) + (df['pct_hhi'] * 0.30) + (df['pct_change'] * 0.30)

    # 3. SKOR FARKI VE DUNKU VERI
    df['prev_quant_score'] = np.nan
    df['score_diff'] = 0.0
    if not df_gecmis.empty:
        son_tarih = df_gecmis['tarih'].max()
        df_son = df_gecmis[df_gecmis['tarih'] == son_tarih]
        eski_map = dict(zip(df_son['ticker'], df_son['quant_score']))
        df['prev_quant_score'] = df['ticker'].map(eski_map).fillna(df['quant_score'])
        df['score_diff'] = df['quant_score'] - df['prev_quant_score']

    return df.sort_values(by='quant_score', ascending=False).reset_index(drop=True)
