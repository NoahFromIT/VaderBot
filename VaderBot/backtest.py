import pandas as pd
from strategy import ReversalStrategy

def run_backtest(file, config):
    df = pd.read_csv(file)
    strat = ReversalStrategy(config["strategy"])

    for _, row in df.iterrows():
        strat.update_candle(row.to_dict())