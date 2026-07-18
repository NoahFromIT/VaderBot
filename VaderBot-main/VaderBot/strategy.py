import pandas as pd
from indicators import calculate_ema

class ReversalStrategy:

    def __init__(self, cfg):
        self.cfg = cfg
        self.df = pd.DataFrame(columns=["time","open","high","low","close","volume"])

    def update_candle(self, candle):
        self.df = pd.concat([self.df, pd.DataFrame([candle])], ignore_index=True)

        # Performance optimization: Cap the history window to avoid growing Pandas memory/CPU usage
        if len(self.df) > 200:
            self.df = self.df.tail(200).reset_index(drop=True)

        if len(self.df) < 20:
            return None

        self.df['ema'] = calculate_ema(self.df['close'], self.cfg['ema_length'])

        row = self.df.iloc[-1]
        ema = row['ema']

        # VWAP passed externally
        vwap = row.get("vwap")
        if vwap is None:
            return None

        # Check extension from VWAP (EMA vs VWAP)
        extension = abs(ema - vwap)
        if extension < self.cfg['extension_threshold_points']:
            return None

        # Define candle metrics to filter out weak reversals/dojis
        high_low_range = row['high'] - row['low']
        body_size = abs(row['close'] - row['open'])
        body_ratio = (body_size / high_low_range) if high_low_range > 0 else 0

        # Read threshold configurations with robust defaults
        min_body_ratio = self.cfg.get('min_candle_body_ratio', 0.5)
        min_body_points = self.cfg.get('min_candle_body_points', 0.0)

        # Check if it's a strong candle close
        if body_ratio < min_body_ratio or body_size < min_body_points:
            return None

        direction = None

        # SHORT: price extended above VWAP, candle crosses & closes below 9 EMA, and candle is red (reversal)
        if ema > vwap and row['close'] < ema and row['open'] > ema and row['close'] < row['open']:
            direction = "SHORT"

        # LONG: price extended below VWAP, candle crosses & closes above 9 EMA, and candle is green (reversal)
        if ema < vwap and row['close'] > ema and row['open'] < ema and row['close'] > row['open']:
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

        # Prevent division by zero and reject trades with stops that are too tight (immediate stopout protection)
        min_stop = self.cfg.get('min_stop_distance_points', 2.0)
        if risk < min_stop:
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