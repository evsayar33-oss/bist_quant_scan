import numpy as np
import pandas as pd
import os

GECMIS_DOSYA = "gecmis_veri.csv"
RVOL_PENCERE = 20
MOM_PENCERE = 5 # N günlük momentum

def gecmis_veriyi_yukle():
    if os.path.exists(GECMIS_DOSYA):
        df = pd.read_csv(GECMIS_DOSYA)
        df['tarih'] = pd.to_datetime(df['tarih'])
        return df
    return pd.DataFrame()

def calculate_quant_scores(df, df_gecmis):
    if df.empty: return df

    # --- 1) ESKİ TEMEL: RVOL HESAPLA ---
    rvol_list = []
    for ticker in df['ticker']:
        hist_v = df_gecmis[df_gecmis['ticker'] == ticker]['volume'].tail(RVOL_PENCERE)
        rvol = df.loc[df['ticker']==ticker, 'volume'].iloc[0] / hist_v.mean() if len(hist_v) >= 5 else 1.0
        rvol_list.append(rvol)
    df['rvol_ratio'] = rvol_list

    # --- 2) YENİ GÜÇLENDİRME: GATEKEEPER (min mantığı) ---
    hhi_mom_list, flow_dense_list = [], []
    for ticker in df['ticker']:
        # HHI Momentum (N günlük değişim)
        hist_hhi = df_gecmis[df_gecmis['ticker'] == ticker]['hhi_score'].tail(MOM_PENCERE)
        hhi_mom = df.loc[df['ticker']==ticker, 'hhi_score'].iloc[0] - (hist_hhi.iloc[0] if len(hist_hhi) > 0 else df.loc[df['ticker']==ticker, 'hhi_score'].iloc[0])
        hhi_mom_list.append(hhi_mom)
        
        # Yabancı Akış Yoğunluğu (Kümülatif Delta / Hacim)
        hist_f = df_gecmis[df_gecmis['ticker'] == ticker]['foreign_ratio'].tail(MOM_PENCERE)
        hist_v = df_gecmis[df_gecmis['ticker'] == ticker]['value_traded'].tail(MOM_PENCERE)
        f_delta = df.loc[df['ticker']==ticker, 'foreign_ratio'].iloc[0] - (hist_f.iloc[0] if len(hist_f) > 0 else df.loc[df['ticker']==ticker, 'foreign_ratio'].iloc[0])
        flow_dense = f_delta / (hist_v.mean() + 1e-9)
        flow_dense_list.append(flow_dense)
        
    df['pct_hhi_mom'] = pd.Series(hhi_mom_list).rank(pct=True) * 100
    df['pct_flow'] = pd.Series(flow_dense_list).rank(pct=True) * 100
    
    # SENİN FORMÜLÜN: Leading Score = min(...)
    df['leading_score'] = df[['pct_hhi_mom', 'pct_flow']].min(axis=1)

    # --- 3) NİHAİ BİRLEŞİK SKOR (SENTEZ) ---
    # %30 RVOL (Hacim Gücü)
    # %20 Fiyat Değişim (Momentum)
    # %50 Leading Score (Kurumsal Teyit: Takas + Yabancı)
    df['pct_rvol'] = df['rvol_ratio'].rank(pct=True) * 100
    df['pct_change'] = df['change_%'].rank(pct=True) * 100
    
    df['quant_score'] = (df['pct_rvol'] * 0.30) + (df['pct_change'] * 0.20) + (df['leading_score'] * 0.50)

    # Fark Hesapla
    df['score_diff'] = 0.0
    if not df_gecmis.empty:
        son_tarih = df_gecmis['tarih'].max()
        df_son = df_gecmis[df_gecmis['tarih'] == son_tarih]
        eski_map = dict(zip(df_son['ticker'], df_son['quant_score']))
        df['score_diff'] = df['quant_score'] - df['ticker'].map(eski_map).fillna(df['quant_score'])

    return df.sort_values(by='quant_score', ascending=False).reset_index(drop=True)
