from datetime import datetime

class CandleBuilder:
    def __init__(self):
        self.current = None

    def update(self, tick):
        ts = datetime.fromtimestamp(tick["timestamp"]/1000)
        minute = (ts.minute // 5) * 5
        key = ts.replace(minute=minute, second=0, microsecond=0)

        if not self.current or self.current["time"] != key:
            finished = self.current
            self.current = {
                "time": key,
                "open": tick["price"],
                "high": tick["price"],
                "low": tick["price"],
                "close": tick["price"],
                "volume": tick["volume"]
            }
            return finished

        c = self.current
        c["high"] = max(c["high"], tick["price"])
        c["low"] = min(c["low"], tick["price"])
        c["close"] = tick["price"]
        c["volume"] += tick["volume"]

        return None