import websocket, json, threading, queue

market_queue = queue.Queue()

def on_message(ws, message):
    market_queue.put(json.loads(message))

def start():
    def run():
        ws = websocket.WebSocketApp("ws://localhost:8765", on_message=on_message)
        ws.run_forever()
    threading.Thread(target=run, daemon=True).start()