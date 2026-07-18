import requests

class ExecutionEngine:

    def __init__(self, config, token, account_id):
        self.cfg = config
        self.token = token
        self.account_id = account_id
        self.endpoint = config["api"]["endpoint"]

    def headers(self):
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    def send_order(self, side, size, stop_ticks=None, target_ticks=None):
        payload = {
            "accountId": self.account_id,
            "contractId": self.cfg["contracts"][0]["id"],
            "side": side,
            "size": size,
            "type": "Market"
        }

        # Add exchange-side bracket orders if provided
        if stop_ticks is not None and stop_ticks > 0:
            payload["stopLossBracket"] = {
                "ticks": int(stop_ticks),
                "type": 4 # 4 = Stop Market order
            }
            print(f"Execution: Attached stop loss bracket at {stop_ticks} ticks.")

        if target_ticks is not None and target_ticks > 0:
            payload["takeProfitBracket"] = {
                "ticks": int(target_ticks),
                "type": 1 # 1 = Limit order
            }
            print(f"Execution: Attached take profit bracket at {target_ticks} ticks.")

        url = f"{self.endpoint}/api/Order/place"
        print(f"Execution: Sending {side} order of size {size} to {url}...")
        
        try:
            r = requests.post(url, json=payload, headers=self.headers(), timeout=10)
            if r.status_code in (200, 201):
                data = r.json()
                print(f"Execution Success: Order filled. Response: {data}")
                return data
            else:
                print(f"Execution Error: Order rejected with code {r.status_code}. Details: {r.text}")
                return None
        except Exception as e:
            print(f"Execution Exception: Connection failed during order submission: {e}")
            return None

    def close_position(self, direction, size):
        side = "Sell" if direction == "LONG" else "Buy"
        # Exiting positions should never attach new brackets
        return self.send_order(side, size)