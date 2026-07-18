import time

class TradeManager:

    def __init__(self, config):
        self.cfg = config
        self.active_trade = None
        self.last_trade_time = 0
        self.session_pnl = 0

    def can_trade(self):
        return (
            time.time() - self.last_trade_time > self.cfg["cooldown_seconds"]
            and self.active_trade is None
        )

    def open_trade(self, signal):
        self.active_trade = {**signal, "trail_active": False}
        self.last_trade_time = time.time()

    def update_price(self, price, ema):
        t = self.active_trade
        if not t:
            return None

        profit = (price - t["entry"]) if t["direction"]=="LONG" else (t["entry"] - price)

        if self.cfg["trail"]["use_trailing"] and profit >= self.cfg["trail"]["activation_points"]:
            t["trail_active"] = True

        # STOP
        if (t["direction"]=="LONG" and price<=t["stop"]) or \
           (t["direction"]=="SHORT" and price>=t["stop"]):
            return "STOP"

        # TARGET
        if not t["trail_active"]:
            if (t["direction"]=="LONG" and price>=t["target"]) or \
               (t["direction"]=="SHORT" and price<=t["target"]):
                return "TARGET"

        # TRAIL
        if t["trail_active"]:
            if (t["direction"]=="LONG" and price<ema) or \
               (t["direction"]=="SHORT" and price>ema):
                return "TRAIL"

        return None