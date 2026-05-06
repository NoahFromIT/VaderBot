class VWAPEngine:
    def __init__(self, mode="tick"):
        self.mode = mode
        self.cum_vol = 0
        self.cum_pv = 0

    def update_tick(self, price, volume):
        if self.mode != "tick":
            return None
        self.cum_vol += volume
        self.cum_pv += price * volume
        return self.cum_pv / self.cum_vol if self.cum_vol else price

    def update_candle(self, candle):
        if self.mode != "candle":
            return None
        self.cum_vol += candle["volume"]
        self.cum_pv += candle["close"] * candle["volume"]
        return self.cum_pv / self.cum_vol