import yfinance as yf


def get_nikkei_225_price():
    """
    日経平均株価 (Nikkei 225) の現在の価格を取得します。
    yfinanceでは日経平均株価のティッカーシンボルは '^N225' です。
    """
    try:
        nikkei = yf.Ticker("^N225")
        # 最新の株価情報を取得
        hist = nikkei.history(period="1d")
        if not hist.empty:
            current_price = hist["Close"].iloc[-1]
            print(f"現在の日経平均株価: {current_price:.2f}")
            return current_price
        else:
            print("日経平均株価のデータを取得できませんでした。")
            return None
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        return None


if __name__ == "__main__":
    get_nikkei_225_price()
