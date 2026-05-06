import pandas as pd
from indicators import calculate_ema

class ReversalStrategy:

    def __init__(self, cfg):
        self.cfg = cfg
        self.df = pd.DataFrame(columns=["time","open","high","low","close","volume"])

    def update_candle(self, candle):
        self.df = pd.concat([self.df, pd.DataFrame([candle])], ignore_index=True)

        if len(self.df) < 20:
            return None

        self.df['ema'] = calculate_ema(self.df['close'], self.cfg['ema_length'])

        row = self.df.iloc[-1]
        ema = row['ema']

        # VWAP passed externally
        vwap = row.get("vwap")
        if vwap is None:
            return None

        extension = abs(ema - vwap)
        if extension < self.cfg['extension_threshold_points']:
            return None

        direction = None

        if ema > vwap and row['close'] < ema and row['open'] > ema:
            direction = "SHORT"

        if ema < vwap and row['close'] > ema and row['open'] < ema:
            direction = "LONG"

        if not direction:
            return None

        return self.validate_rr(direction, ema, vwap)

    def validate_rr(self, direction, ema, vwap):
        recent = self.df.tail(10)
        entry = self.df.iloc[-1]['close']

        if direction == "LONG":
            stop = recent['low'].min()
            target = vwap
        else:
            stop = recent['high'].max()
            target = vwap

        risk = abs(entry - stop)
        reward = abs(target - entry)

        if risk == 0:
            return None

        rr = reward / risk

        if rr >= self.cfg['risk_reward_min']:
            return {
                "direction": direction,
                "entry": entry,
                "stop": stop,
                "target": target,
                "ema": ema
            }