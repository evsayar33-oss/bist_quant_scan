import requests
import pandas as pd
 
 
def get_bist_tickers():
    """TradingView API uzerinden BIST hisse listesini ve gunluk verileri ceker."""
    url = "https://scanner.tradingview.com/turkey/scan"
    payload = {
        "filter": [{"left": "type", "operation": "equal", "right": "stock"}],
        "columns": ["name", "close", "volume", "change", "Value.Traded"],
        "sort": {"sortBy": "Value.Traded", "sortOrder": "desc"},
        "range": [0, 200]
    }
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        data = response.json()
        rows = []
        for item in data.get("data", []):
            d = item["d"]
            rows.append({
                "ticker": d[0],
                "close": d[1],
                "volume": d[2],
                "change_%": d[3],
                "value_traded": d[4]
            })
        return pd.DataFrame(rows)
    except Exception as e:
        print(f"TradingView veri cekme hatasi: {e}")
        return pd.DataFrame()
 
 
def get_takas_data(ticker):
    """
    Is Yatirim web servisinden hissenin ilk 5 ve 15 kurum saklama oranlarini ceker.
    NOT (kapsam disi birakildi): bu fonksiyon hala dogrulanmamis/simule bir uc noktaya
    dayaniyor - asagidaki "Operasyonel Notlar" bolumune bakin.
        """
    url = "https://www.isyatirim.com.tr/_layouts/15/IsYatirim.YatirimDanismanligi/PiyasaVerileri.aspx/GetHisseTakasData"
    try:
        headers = {"User-Agent": "Mozilla/5.0", "X-Requested-With": "XMLHttpRequest"}
        params = {"hisseKodu": ticker}
        res = requests.get(url, params=params, headers=headers, timeout=5)
        if res.status_code == 200:
            json_data = res.json()
            shares = json_data.get("d", [])
            if shares:
                return [float(x.get("Yuzde", 0)) for x in shares[:15]]
    except Exception:
        pass
    return []
 
