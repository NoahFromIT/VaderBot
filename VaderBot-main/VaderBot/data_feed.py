import websocket
import json
import threading
import queue
import subprocess
import os
import time
import atexit

market_queue = queue.Queue()
bridge_process = None

def on_message(ws, message):
    try:
        data = json.loads(message)
        market_queue.put(data)
    except Exception as e:
        print(f"Data Feed Error: Failed to parse message: {e}")

def on_error(ws, error):
    # Print warning instead of crashing
    print(f"Data Feed Warning: WebSocket error: {error}")

def on_close(ws, close_status_code, close_msg):
    print("Data Feed: WebSocket connection closed.")

def start(token, contract_id):
    global bridge_process

    # 1. Start the Node.js bridge process as a background subprocess
    def run_bridge():
        global bridge_process
        bridge_path = os.path.join(os.path.dirname(__file__), "bridge", "bridge.js")
        
        env = os.environ.copy()
        env["TOPSTEP_TOKEN"] = token
        env["TOPSTEP_CONTRACT"] = contract_id

        print("Data Feed: Launching local SignalR-to-WebSocket bridge...")
        try:
            bridge_process = subprocess.Popen(
                ["node", bridge_path],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Forward stdout/stderr logs from the Node process to Python console
            def log_stream(stream, prefix):
                for line in iter(stream.readline, ""):
                    print(f"[{prefix}] {line.strip()}")
            
            threading.Thread(target=log_stream, args=(bridge_process.stdout, "Node Bridge"), daemon=True).start()
            threading.Thread(target=log_stream, args=(bridge_process.stderr, "Node Bridge Error"), daemon=True).start()
            
            bridge_process.wait()
            print(f"Data Feed: Bridge process exited with code {bridge_process.returncode}")
        except Exception as e:
            print(f"Data Feed Error: Failed to launch Node.js bridge: {e}")
            print("Verify Node.js is installed and the 'node' binary is in your system PATH.")

    threading.Thread(target=run_bridge, daemon=True).start()

    # 2. Start WebSocket client connecting to the bridge server
    def run_websocket():
        # Give Node process 1 second to start up before the first connection attempt
        time.sleep(1.0)
        while True:
            try:
                print("Data Feed: Connecting to local bridge at ws://localhost:8765...")
                ws = websocket.WebSocketApp(
                    "ws://localhost:8765",
                    on_message=on_message,
                    on_error=on_error,
                    on_close=on_close
                )
                ws.run_forever(ping_interval=10, ping_timeout=5)
            except Exception as e:
                print(f"Data Feed Connection Error: {e}")
            print("Data Feed: Reconnecting in 3 seconds...")
            time.sleep(3)

    threading.Thread(target=run_websocket, daemon=True).start()

def cleanup_bridge():
    global bridge_process
    if bridge_process and bridge_process.poll() is None:
        print("Data Feed: Cleaning up bridge process...")
        bridge_process.terminate()
        try:
            bridge_process.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            bridge_process.kill()

atexit.register(cleanup_bridge)