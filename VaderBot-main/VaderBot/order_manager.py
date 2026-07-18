# order_manager.py

class OrderManager:

    def __init__(self):
        self.active_orders = {}

    def register_bracket(self, entry_id, stop_id, target_id):
        self.active_orders[entry_id] = {
            "stop": stop_id,
            "target": target_id
        }

    def on_fill(self, order_id, executor):
        for entry, orders in self.active_orders.items():
            if order_id == orders["stop"]:
                executor.cancel_order(orders["target"])
                print("OCO: Target cancelled")

            elif order_id == orders["target"]:
                executor.cancel_order(orders["stop"])
                print("OCO: Stop cancelled")