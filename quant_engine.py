import numpy as np
import pandas as pd
import os

GECMIS_DOSYA = "gecmis_veri.csv"
RVOL_PENCERE = 20
MOM_PENCERE = 5 

def gecmis_veriyi_yukle():
    if os.path.exists(GECMIS_DOSYA):
        try:
            df = pd.read_csv(GECMIS_DOSYA)
            df['tarih'] = pd.to_datetime(df['tarih'])
            return df
        except: return pd.DataFrame()
    return pd.DataFrame()

def calculate_quant_scores(df, df_gecmis):
    if df.empty: return df

    # 1) RVOL (0-100 Skalası)
    rvol_list = []
    for ticker in df['ticker']:
        hist_v = df_gecmis[df_gecmis['ticker'] == ticker]['volume'].tail(RVOL_PENCERE) if not df_gecmis.empty else []
        rvol = df.loc[df['ticker']==ticker, 'volume'].iloc[0] / (hist_v.mean() + 1e-9) if len(hist_v) >= 5 else 1.0
        rvol_list.append(rvol)
    df['rvol_ratio'] = rvol_list
    df['pct_rvol'] = df['rvol_ratio'].rank(pct=True) * 100

    # 2) Gatekeeper (HHI Mom + Yabancı Akış - 0-100 Skalası)
    hhi_mom_list, flow_dense_list = [], []
    for ticker in df['ticker']:
        ticker_gecmis = df_gecmis[df_gecmis['ticker'] == ticker] if not df_gecmis.empty else pd.DataFrame()
        
        # HHI Momentum
        hist_hhi = ticker_gecmis['hhi_score'].tail(MOM_PENCERE)
        h_now = df.loc[df['ticker']==ticker, 'hhi_score'].iloc[0]
        hhi_mom = h_now - (hist_hhi.iloc[0] if len(hist_hhi)>0 else h_now)
        hhi_mom_list.append(hhi_mom)
        
        # Yabancı Akış
        hist_f = ticker_gecmis['foreign_ratio'].tail(MOM_PENCERE)
        hist_v = ticker_gecmis['value_traded'].tail(MOM_PENCERE)
        f_now = df.loc[df['ticker']==ticker, 'foreign_ratio'].iloc[0]
        f_delta = f_now - (hist_f.iloc[0] if len(hist_f)>0 else f_now)
        flow_dense = f_delta / (hist_v.mean() + 1e-9) if len(hist_v)>0 else 0
        flow_dense_list.append(flow_dense)
        
    df['pct_hhi_mom'] = pd.Series(hhi_mom_list).rank(pct=True) * 100
    df['pct_flow'] = pd.Series(flow_dense_list).rank(pct=True) * 100
    df['leading_score'] = df[['pct_hhi_mom', 'pct_flow']].min(axis=1)

    # 3) Nihai Skor (Tamamı 0-100 arası verilerden oluşur)
    df['pct_change'] = df['change_%'].rank(pct=True) * 100
    # %30 Hacim Gücü + %20 Fiyat İvmesi + %50 Kurumsal Gatekeeper
    df['quant_score'] = (df['pct_rvol'] * 0.30) + (df['pct_change'] * 0.20) + (df['leading_score'] * 0.50)

    # 4) Skor Farkı (Düne Göre)
    df['prev_quant_score'] = np.nan
    df['score_diff'] = 0.0
    if not df_gecmis.empty and 'quant_score' in df_gecmis.columns:
        son_tarih = df_gecmis['tarih'].max()
        df_son = df_gecmis[df_gecmis['tarih'] == son_tarih]
        eski_map = dict(zip(df_son['ticker'], df_son['quant_score']))
        df['prev_quant_score'] = df['ticker'].map(eski_map).fillna(df['quant_score'])
        df['score_diff'] = df['quant_score'] - df['prev_quant_score']

    return df.sort_values(by='quant_score', ascending=False).reset_index(drop=True)
