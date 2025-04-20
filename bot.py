import ccxt
import time
import requests
import datetime
from configparser import ConfigParser

def load_config():
    config = ConfigParser()
    config.read("config.ini")
    return config

def send_telegram_message(bot_token, chat_id, message):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message}
    requests.post(url, data=payload)

def get_new_symbols(exchange):
    markets = exchange.load_markets()
    now = time.time()
    new_symbols = []
    for symbol, data in markets.items():
        if "/USDT" not in symbol or symbol.endswith("3L/USDT") or symbol.endswith("3S/USDT"):
            continue
        since = data.get("info", {}).get("created_date")
        if since:
            try:
                created = int(datetime.datetime.strptime(since, "%Y-%m-%d %H:%M:%S").timestamp())
                age_days = (now - created) / 86400
                if age_days <= 100:
                    new_symbols.append(symbol)
            except Exception:
                continue
    return new_symbols

def is_step_pattern(candles):
    closes = [c[4] for c in candles]
    volumes = [c[5] for c in candles]
    avg_volume = sum(volumes[-10:]) / 10

    # 3 свечи роста
    if closes[-3] < closes[-2] < closes[-1]:
        # Всплеск объема минимум в 3 раза (сравниваем 3 свечи назад со средним до)
        if volumes[-3] > avg_volume * 3:
            # И объемы не падают
            if volumes[-2] >= volumes[-3] * 0.8 and volumes[-1] >= volumes[-2] * 0.8:
                return True
    return False

def main():
    config = load_config()
    exchange = ccxt.bitmart({
        "apiKey": config["bitmart"]["api_key"],
        "secret": config["bitmart"]["api_secret"],
        "enableRateLimit": True,
    })

    bot_token = config["telegram"]["bot_token"]
    chat_id = config["telegram"]["chat_id"]
    notified = set()

    while True:
        try:
            symbols = get_new_symbols(exchange)
            for symbol in symbols:
                try:
                    ticker = exchange.fetch_ticker(symbol)
                    if ticker["quoteVolume"] > 500000:
                        continue  # Пропускаем высоколиквидные

                    ohlcv = exchange.fetch_ohlcv(symbol, timeframe="1m", limit=20)
                    if is_step_pattern(ohlcv):
                        if symbol not in notified:
                            msg = f"🚀 Найдена лесенка: {symbol}"
                            send_telegram_message(bot_token, chat_id, msg)
                            notified.add(symbol)
                except Exception:
                    continue
            time.sleep(60)
        except Exception as e:
            print("Ошибка:", e)
            time.sleep(60)

if __name__ == "__main__":
    main()
