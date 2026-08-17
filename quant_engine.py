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
        except:
            return pd.DataFrame()
    return pd.DataFrame()

def calculate_hhi(takas_shares):
    if not takas_shares or sum(takas_shares) == 0:
        return 0.0
    shares = np.array(takas_shares)
    normalized_shares = (shares / shares.sum()) * 100
    return float(np.sum(normalized_shares ** 2))

def calculate_quant_scores(df, df_gecmis):
    if df.empty: return df

    # 1) RVOL Hesapla
    rvol_oranlari = []
    for _, row in df.iterrows():
        ticker = row['ticker']
        gecmis_hacim = df_gecmis[df_gecmis['ticker'] == ticker]['volume'].tail(RVOL_PENCERE) if not df_gecmis.empty else []
        if len(gecmis_hacim) >= MIN_GECMIS_GUN:
            rvol = row['volume'] / gecmis_hacim.mean()
        else:
            rvol = np.nan
        rvol_oranlari.append(rvol)
    
    df['rvol_ratio'] = rvol_oranlari
    yeterli_gecmis = df['rvol_ratio'].notna()
    df['rvol_ratio'] = df['rvol_ratio'].fillna(1.0)
    df['gecmis_yetersiz'] = ~yeterli_gecmis

    # 2) Skorları Hesapla
    df['pct_rvol'] = df['rvol_ratio'].rank(pct=True) * 100
    df['pct_change'] = df['change_%'].rank(pct=True) * 100
    df['pct_hhi'] = df['hhi_score'].rank(pct=True) * 100
    df['quant_score'] = (df['pct_rvol'] * 0.40) + (df['pct_change'] * 0.30) + (df['pct_hhi'] * 0.30)

    # 3) SKOR FARKLARINI HESAPLA (ÇIKIŞ ANALİZİ İÇİN)
    df['prev_quant_score'] = np.nan
    df['score_diff'] = 0.0

    if not df_gecmis.empty:
        # En son tarihi bul (bugünü hariç tutarak)
        gecmis_tarihler = df_gecmis['tarih'].dt.date.unique()
        if len(gecmis_tarihler) >= 1:
            son_tarih = max(gecmis_tarihler)
            df_son = df_gecmis[df_gecmis['tarih'].dt.date == son_tarih]
            eski_skor_map = dict(zip(df_son['ticker'], df_son['quant_score']))
            
            df['prev_quant_score'] = df['ticker'].map(eski_skor_map)
            # Eğer dün yoksa bugünü yaz ki fark 0 olsun
            df['prev_quant_score'] = df['prev_quant_score'].fillna(df['quant_score'])
            df['score_diff'] = df['quant_score'] - df['prev_quant_score']

    return df.sort_values(by='quant_score', ascending=False).reset_index(drop=True)
