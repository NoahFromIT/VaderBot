import requests

class ExecutionEngine:

    def __init__(self, config, token):
        self.cfg = config
        self.token = token
        self.endpoint = config["api"]["endpoint"]

    def headers(self):
        return {"Authorization": f"Bearer {self.token}"}

    def send_order(self, side, size):
        return requests.post(f"{self.endpoint}/api/Order/place",
            json={
                "contractId": self.cfg["contracts"][0]["id"],
                "side": side,
                "size": size,
                "type": "Market"
            },
            headers=self.headers())

    def close_position(self, direction, size):
        side = "Sell" if direction=="LONG" else "Buy"
        self.send_order(side, size)