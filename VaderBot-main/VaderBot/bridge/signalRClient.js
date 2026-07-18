const signalR = require('@microsoft/signalr');
const WebSocket = require('ws');
const EventEmitter = require('events');

const signalrEvents = new EventEmitter();

function setupSignalRConnection(token, contractId) {
  if (!token || token === "YOUR_TOKEN") {
    console.error("SignalR Error: Invalid or missing token.");
    return;
  }

  console.log(`Initializing SignalR connection to Market Hub for contract: ${contractId}...`);

  const connection = new signalR.HubConnectionBuilder()
    .withUrl("https://rtc.topstepx.com/hubs/market", {
      transport: signalR.HttpTransportType.WebSockets,
      skipNegotiation: true,
      webSocket: WebSocket,
      accessTokenFactory: () => token
    })
    .withAutomaticReconnect()
    .build();

  connection.onclose((error) => {
    console.error("SignalR: Connection closed.", error ? error.message : "");
  });

  connection.onreconnecting((error) => {
    console.warn("SignalR: Connection lost. Reconnecting...", error ? error.message : "");
  });

  connection.onreconnected((connectionId) => {
    console.log("SignalR: Connection re-established. Connection ID:", connectionId);
    subscribe(connection, contractId);
  });

  async function start() {
    try {
      await connection.start();
      console.log("SignalR: Connection established successfully.");
      await subscribe(connection, contractId);
    } catch (err) {
      console.error("SignalR: Connection failed to start:", err.message);
      console.log("SignalR: Retrying in 5 seconds...");
      setTimeout(start, 5000);
    }
  }

  connection.on('GatewayTrade', (incomingContractId, tradeData) => {
    if (incomingContractId === contractId) {
      signalrEvents.emit('trade', {
        contractId: incomingContractId,
        data: tradeData
      });
    }
  });

  start();
}

async function subscribe(connection, contractId) {
  try {
    console.log(`SignalR: Subscribing to trades for contract: ${contractId}...`);
    await connection.invoke("SubscribeContractTrades", contractId);
    console.log(`SignalR: Successfully subscribed to ${contractId}`);
  } catch (err) {
    console.error(`SignalR: Subscription failed for ${contractId}:`, err.message);
  }
}

module.exports = {
  setupSignalRConnection,
  signalrEvents
};
