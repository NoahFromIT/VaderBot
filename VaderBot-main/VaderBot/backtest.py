import pandas as pd
import json
import os
import sys

# Ensure Python can find strategy.py and indicators.py in the same folder
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from strategy import ReversalStrategy

def run_backtest(file, config):
    if not os.path.exists(file):
        print(f"Backtest Error: Data file '{file}' not found at path: {file}")
        return

    print(f"Backtest: Loading data from {file}...")
    try:
        df = pd.read_csv(file)
    except Exception as e:
        print(f"Backtest Error: Failed to read CSV file: {e}")
        return
    
    # Standardize column headers to lowercase
    df.columns = [c.lower() for c in df.columns]
    
    required = ["time", "open", "high", "low", "close", "volume"]
    for col in required:
        if col not in df.columns:
            print(f"Backtest Error: Missing required column '{col}' in CSV.")
            return

    strat = ReversalStrategy(config["strategy"])
    
    active_trade = None
    trades = []
    
    cum_vol = 0
    cum_pv = 0
    
    print("Backtest: Simulating trading strategy...")
    
    for idx, row in df.iterrows():
        candle = row.to_dict()
        
        # Calculate dynamic VWAP if missing from CSV
        if "vwap" not in candle:
            vol = candle.get("volume", 1)
            cum_vol += vol
            cum_pv += candle["close"] * vol
            candle["vwap"] = cum_pv / cum_vol if cum_vol > 0 else candle["close"]

        # Run strategy candle update
        signal = strat.update_candle(candle)
        
        # Update active trade exit check
        if active_trade:
            entry = active_trade["entry"]
            stop = active_trade["stop"]
            target = active_trade["target"]
            direction = active_trade["direction"]
            trail_active = active_trade.get("trail_active", False)
            
            # Get latest EMA calculated by the strategy
            ema = strat.df.iloc[-1]["ema"] if "ema" in strat.df.columns else candle["close"]
            
            # Check trailing stop activation
            activation_pts = config["trail"]["activation_points"]
            use_trailing = config["trail"]["use_trailing"]
            
            if direction == "LONG":
                profit = candle["high"] - entry
                if use_trailing and profit >= activation_pts:
                    trail_active = True
                    active_trade["trail_active"] = True
                
                # Check exit conditions
                if candle["low"] <= stop:
                    trades.append({
                        "direction": direction,
                        "entry_time": active_trade["time"],
                        "exit_time": candle["time"],
                        "entry": entry,
                        "exit": stop,
                        "pnl": stop - entry,
                        "reason": "STOP"
                    })
                    active_trade = None
                elif not trail_active and candle["high"] >= target:
                    trades.append({
                        "direction": direction,
                        "entry_time": active_trade["time"],
                        "exit_time": candle["time"],
                        "entry": entry,
                        "exit": target,
                        "pnl": target - entry,
                        "reason": "TARGET"
                    })
                    active_trade = None
                elif trail_active and candle["low"] < ema:
                    exit_price = min(candle["close"], ema)
                    trades.append({
                        "direction": direction,
                        "entry_time": active_trade["time"],
                        "exit_time": candle["time"],
                        "entry": entry,
                        "exit": exit_price,
                        "pnl": exit_price - entry,
                        "reason": "TRAIL"
                    })
                    active_trade = None
            else: # SHORT
                profit = entry - candle["low"]
                if use_trailing and profit >= activation_pts:
                    trail_active = True
                    active_trade["trail_active"] = True
                
                # Check exit conditions
                if candle["high"] >= stop:
                    trades.append({
                        "direction": direction,
                        "entry_time": active_trade["time"],
                        "exit_time": candle["time"],
                        "entry": entry,
                        "exit": stop,
                        "pnl": entry - stop,
                        "reason": "STOP"
                    })
                    active_trade = None
                elif not trail_active and candle["low"] <= target:
                    trades.append({
                        "direction": direction,
                        "entry_time": active_trade["time"],
                        "exit_time": candle["time"],
                        "entry": entry,
                        "exit": target,
                        "pnl": entry - target,
                        "reason": "TARGET"
                    })
                    active_trade = None
                elif trail_active and candle["high"] > ema:
                    exit_price = max(candle["close"], ema)
                    trades.append({
                        "direction": direction,
                        "entry_time": active_trade["time"],
                        "exit_time": candle["time"],
                        "entry": entry,
                        "exit": exit_price,
                        "pnl": entry - exit_price,
                        "reason": "TRAIL"
                    })
                    active_trade = None

        # Check for new trade signal
        if not active_trade and signal:
            active_trade = {
                "direction": signal["direction"],
                "entry": signal["entry"],
                "stop": signal["stop"],
                "target": signal["target"],
                "time": candle["time"],
                "trail_active": False
            }
            print(f"Signal: Entered {signal['direction']} @ {signal['entry']} (Stop: {signal['stop']}, Target: {signal['target']}) at {candle['time']}")

    # Print summary statistics
    print("\n" + "="*60)
    print("                    BACKTEST REPORT")
    print("="*60)
    total_trades = len(trades)
    if total_trades == 0:
        print("No trades were executed during the backtest.")
        print("="*60)
        return

    wins = [t for t in trades if t["pnl"] > 0]
    losses = [t for t in trades if t["pnl"] <= 0]
    total_pnl = sum([t["pnl"] for t in trades])
    win_rate = (len(wins) / total_trades) * 100
    
    print(f"Total Trades Simulated: {total_trades}")
    print(f"Wins:                  {len(wins)} ({win_rate:.1f}%)")
    print(f"Losses:                {len(losses)} ({100 - win_rate:.1f}%)")
    print(f"Net Profit/Loss:       {total_pnl:+.2f} points")
    print("-" * 60)
    print("Executed Trade Logs:")
    for i, t in enumerate(trades):
        print(f"  {i+1:2d}. {t['direction']:5s} | Enter: {t['entry']:.2f} -> Exit: {t['exit']:.2f} | PnL: {t['pnl']:+7.2f} pts | Reason: {t['reason']}")
    print("="*60)

if __name__ == "__main__":
    # Load config and execute
    config_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(config_dir, "config.json")
    if os.path.exists(config_path):
        config = json.load(open(config_path))
        data_file = config.get("backtest", {}).get("data_file", "historical_data.csv")
        # Ensure path is absolute and relative to config location
        if not os.path.isabs(data_file):
            data_path = os.path.normpath(os.path.join(config_dir, data_file))
        else:
            data_path = data_file
        
        run_backtest(data_path, config)
    else:
        print("Error: config.json not found in directory:", config_dir)