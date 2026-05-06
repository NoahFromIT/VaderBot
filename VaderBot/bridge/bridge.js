const WebSocket = require('ws');
const { setupSignalRConnection, signalrEvents } = require('./signalRClient');

const wss = new WebSocket.Server({ port: 8765 });

function broadcast(data) {
  wss.clients.forEach(client => {
    if (client.readyState === WebSocket.OPEN) {
      client.send(JSON.stringify(data));
    }
  });
}

setupSignalRConnection("YOUR_TOKEN", "CON.F.US.MNQ.M25");

signalrEvents.on('trade', ({ contractId, data }) => {
  broadcast({
    type: "trade",
    contractId,
    price: data.p,
    volume: data.v,
    timestamp: Date.now()
  });
});