const WebSocket = require('ws');
const { setupSignalRConnection, signalrEvents } = require('./signalRClient');

const wss = new WebSocket.Server({ port: 8765 });

console.log("WebSocket: Local server listening on port 8765...");

function broadcast(data) {
  wss.clients.forEach(client => {
    if (client.readyState === WebSocket.OPEN) {
      client.send(JSON.stringify(data));
    }
  });
}

const token = process.env.TOPSTEP_TOKEN;
const contractId = process.env.TOPSTEP_CONTRACT;

if (!token) {
  console.error("Bridge Error: TOPSTEP_TOKEN environment variable is required.");
  process.exit(1);
}

if (!contractId) {
  console.error("Bridge Error: TOPSTEP_CONTRACT environment variable is required.");
  process.exit(1);
}

setupSignalRConnection(token, contractId);

signalrEvents.on('trade', ({ contractId, data }) => {
  broadcast({
    type: "trade",
    contractId,
    price: data.p,
    volume: data.v,
    timestamp: Date.now()
  });
});