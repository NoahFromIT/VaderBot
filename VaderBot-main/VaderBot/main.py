import json
import time
import requests
import queue
from data_feed import start, market_queue
from candle_builder import CandleBuilder
from vwap_engine import VWAPEngine
from strategy import ReversalStrategy
from trade_manager import TradeManager
from execution import ExecutionEngine
from session_filter import in_session

def authenticate(cfg):
    url = f"{cfg['api']['endpoint']}/api/Auth/loginKey"
    print(f"Auth: Authenticating user {cfg['api']['username']} at {url}...")
    try:
        r = requests.post(url,
            json={"userName": cfg["api"]["username"], "apiKey": cfg["api"]["api_key"]},
            timeout=10)
        if r.status_code == 200:
            token = r.json().get("token")
            if token:
                print("Auth: Authenticated successfully.")
                return token
        print(f"Auth Error: Authentication failed with status {r.status_code}: {r.text}")
        return None
    except Exception as e:
        print(f"Auth Exception: Connection failed: {e}")
        return None

def get_active_account(cfg, token):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    url = f"{cfg['api']['endpoint']}/api/Account/search"
    print(f"Auth: Retrieving active account from {url}...")
    try:
        r = requests.post(url, json={"onlyActiveAccounts": True}, headers=headers, timeout=10)
        if r.status_code == 200:
            accounts = r.json()
            if isinstance(accounts, list) and len(accounts) > 0:
                account_id = accounts[0].get("id")
                account_name = accounts[0].get("name")
                print(f"Auth: Selected active account '{account_name}' (ID: {account_id})")
                return account_id
            else:
                print("Auth Error: No active accounts found in search results.")
        else:
            print(f"Auth Error: Account search failed with status {r.status_code}: {r.text}")
        return None
    except Exception as e:
        print(f"Auth Exception: Failed to search accounts: {e}")
        return None

def process_tick(tick, config, strategy, trade_manager, executor, candle_builder, vwap_engine):
    price = tick["price"]
    vol = tick["volume"]
    ts = tick.get("timestamp")

    # Update tick-based VWAP
    vwap = vwap_engine.update_tick(price, vol, ts)

    # Update candle builder
    candle = candle_builder.update(tick)

    if candle:
        # If candle-based VWAP is selected, compute it
        if config["strategy"]["vwap_mode"] == "candle":
            vwap = vwap_engine.update_candle(candle)

        candle["vwap"] = vwap
        signal = strategy.update_candle(candle)

        if signal and trade_manager.can_trade() and in_session(config["session"]):
            direction = signal["direction"]
            size = config["strategy"]["position_size"]

            # Calculate stop/target ticks for exchange-side bracket orders
            stop_ticks = None
            target_ticks = None
            if config["strategy"].get("use_exchange_brackets", False):
                tick_size = config["contracts"][0]["tick_size"]
                risk = abs(signal["entry"] - signal["stop"])
                reward = abs(signal["target"] - signal["entry"])
                stop_ticks = max(1, int(round(risk / tick_size)))
                target_ticks = max(1, int(round(reward / tick_size)))

            order_side = "Buy" if direction == "LONG" else "Sell"
            order_res = executor.send_order(order_side, size, stop_ticks, target_ticks)
            
            if order_res:
                print(f"Main: Entered {direction} position. Entry: {signal['entry']}, Stop: {signal['stop']}, Target: {signal['target']}")
                trade_manager.open_trade(signal)
            else:
                print("Main Error: Order placement failed, skipping trade entry tracking.")

    # Manage exits on active trade
    if trade_manager.active_trade:
        ema = strategy.df.iloc[-1]["ema"]
        exit_reason = trade_manager.update_price(price, ema)

        if exit_reason:
            t = trade_manager.active_trade
            use_brackets = config["strategy"].get("use_exchange_brackets", False)
            
            if use_brackets and exit_reason in ("STOP", "TARGET"):
                # Exchange bracket orders automatically closed the position
                print(f"Main: Position closed on exchange via {exit_reason}.")
            else:
                # Local trail close, or fallback exit order
                print(f"Main: Position exit triggered locally by {exit_reason}. Closing position...")
                executor.close_position(t["direction"], config["strategy"]["position_size"])
                
            trade_manager.active_trade = None

def main():
    import os
    config_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(config_dir, "config.json")
    config = json.load(open(config_path))

    token = authenticate(config)
    if not token:
        print("Main: Critical Error - Authentication failed. Exiting.")
        return

    account_id = get_active_account(config, token)
    if not account_id:
        print("Main: Critical Error - No active account found. Exiting.")
        return

    # Pass token and contract id to data feed to boot Node bridge automatically
    contract_id = config["contracts"][0]["id"]
    start(token, contract_id)

    strategy = ReversalStrategy(config["strategy"])
    trade_manager = TradeManager(config["strategy"])
    executor = ExecutionEngine(config, token, account_id)

    candle_builder = CandleBuilder()
    vwap_engine = VWAPEngine(config["strategy"]["vwap_mode"], config["session"]["timezone"])

    print("Main: Bot is running. Waiting for ticks...")

    while True:
        try:
            # Block up to 1 second waiting for the next tick to prevent CPU spinning
            tick = market_queue.get(timeout=1.0)
            process_tick(tick, config, strategy, trade_manager, executor, candle_builder, vwap_engine)

            # Instantly drain and process any queued ticks to maintain zero-lag execution
            while not market_queue.empty():
                tick = market_queue.get_nowait()
                process_tick(tick, config, strategy, trade_manager, executor, candle_builder, vwap_engine)

        except queue.Empty:
            # Check connection or do idle tasks if needed
            pass
        except KeyboardInterrupt:
            print("Main: Shutting down bot gracefully...")
            break
        except Exception as e:
            print(f"Main Error: Unexpected exception in execution loop: {e}")
            time.sleep(1) # Prevent tight loop error spinning

if __name__ == "__main__":
    main()