import pandas as pd

def calculate_ema(series, length):
    return series.ewm(span=length, adjust=False).mean()