from datetime import datetime
import pytz

class VWAPEngine:
    def __init__(self, mode="tick", timezone="US/Eastern"):
        self.mode = mode
        self.timezone = pytz.timezone(timezone)
        self.cum_vol = 0
        self.cum_pv = 0
        self.last_date = None

    def _check_reset(self, timestamp_ms):
        if not timestamp_ms:
            return
        
        # Convert timestamp to local timezone to detect day transition
        dt = datetime.fromtimestamp(timestamp_ms / 1000.0, self.timezone)
        current_date = dt.date()
        
        if self.last_date is not None and current_date != self.last_date:
            print(f"VWAP: Resetting cumulative volume and price-volume for new day: {current_date}")
            self.cum_vol = 0
            self.cum_pv = 0
            
        self.last_date = current_date

    def update_tick(self, price, volume, timestamp_ms=None):
        if self.mode != "tick":
            return None
        
        if timestamp_ms:
            self._check_reset(timestamp_ms)
            
        self.cum_vol += volume
        self.cum_pv += price * volume
        return self.cum_pv / self.cum_vol if self.cum_vol else price

    def update_candle(self, candle):
        if self.mode != "candle":
            return None
        
        if "time" in candle:
            c_time = candle["time"]
            if isinstance(c_time, datetime):
                c_date = c_time.date() if c_time.tzinfo is None else c_time.astimezone(self.timezone).date()
                if self.last_date is not None and c_date != self.last_date:
                    print(f"VWAP: Resetting (candle mode) for new day: {c_date}")
                    self.cum_vol = 0
                    self.cum_pv = 0
                self.last_date = c_date

        self.cum_vol += candle["volume"]
        self.cum_pv += candle["close"] * candle["volume"]
        return self.cum_pv / self.cum_vol if self.cum_vol else candle["close"]