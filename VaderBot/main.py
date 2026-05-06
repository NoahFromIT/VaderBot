import json, time, requests
from data_feed import start, market_queue
from candle_builder import CandleBuilder
from vwap_engine import VWAPEngine
from strategy import ReversalStrategy
from trade_manager import TradeManager
from execution import ExecutionEngine
from session_filter import in_session

def authenticate(cfg):
    r = requests.post(f"{cfg['api']['endpoint']}/api/Auth/loginKey",
        json={"userName": cfg["api"]["username"], "apiKey": cfg["api"]["api_key"]})
    return r.json().get("token")

def main():
    config = json.load(open("config.json"))

    token = authenticate(config)

    start()

    strategy = ReversalStrategy(config["strategy"])
    trade_manager = TradeManager(config["strategy"])
    executor = ExecutionEngine(config, token)

    candle_builder = CandleBuilder()
    vwap_engine = VWAPEngine(config["strategy"]["vwap_mode"])

    while True:

        if not market_queue.empty():
            tick = market_queue.get()

            price = tick["price"]
            vol = tick["volume"]

            vwap = vwap_engine.update_tick(price, vol)

            candle = candle_builder.update(tick)

            if candle:

                if config["strategy"]["vwap_mode"] == "candle":
                    vwap = vwap_engine.update_candle(candle)

                candle["vwap"] = vwap

                signal = strategy.update_candle(candle)

                if signal and trade_manager.can_trade() and in_session(config["session"]):
                    executor.send_order("Buy" if signal["direction"]=="LONG" else "Sell", 1)
                    trade_manager.open_trade(signal)

            if trade_manager.active_trade:
                ema = strategy.df.iloc[-1]["ema"]
                exit_reason = trade_manager.update_price(price, ema)

                if exit_reason:
                    t = trade_manager.active_trade
                    executor.close_position(t["direction"], 1)
                    trade_manager.active_trade = None

        time.sleep(0.1)

if __name__ == "__main__":
    main()