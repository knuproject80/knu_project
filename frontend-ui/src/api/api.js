import { Client } from '@stomp/stompjs';

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8080/ws';

const TOPICS = {
  uiGlobal: '/topic/ui/global',
  uiSession: (sessionId) => `/topic/ui/${sessionId}`,
  frontAck: '/topic/front/ack',
};

const DESTINATIONS = {
  frontEvents: '/app/front/events',
  frontAck: '/app/front/ack',
};

let client = null;
let connectPromise = null;
let isConnected = false;
const activeSubscriptions = new Map();

function safeJsonParse(value) {
  try {
    return JSON.parse(value);
  } catch {
    return value;
  }
}

function ensureClient() {
  if (client) return client;

  client = new Client({
    brokerURL: WS_URL,
    reconnectDelay: 0,
    heartbeatIncoming: 4000,
    heartbeatOutgoing: 4000,
    debug: () => {},
  });

  client.onConnect = () => {
    isConnected = true;
  };

  client.onWebSocketClose = () => {
    isConnected = false;
    connectPromise = null;
  };

  client.onWebSocketError = (error) => {
    console.error('WebSocket error:', error);
  };

  client.onStompError = (frame) => {
    console.error('Broker reported error:', frame.headers?.message, frame.body);
  };

  return client;
}

export async function connectStomp() {
  if (client && isConnected) return client;
  if (connectPromise) return connectPromise;

  const stompClient = ensureClient();

  connectPromise = new Promise((resolve, reject) => {
    let settled = false;

    const cleanup = () => {
      stompClient.onConnect = originalOnConnect;
      stompClient.onWebSocketError = originalOnWebSocketError;
    };

    const originalOnConnect = stompClient.onConnect;
    const originalOnWebSocketError = stompClient.onWebSocketError;

    stompClient.onConnect = (frame) => {
      isConnected = true;
      originalOnConnect?.(frame);
      if (!settled) {
        settled = true;
        cleanup();
        resolve(stompClient);
      }
    };

    stompClient.onWebSocketError = (error) => {
      originalOnWebSocketError?.(error);
      if (!settled) {
        settled = true;
        cleanup();
        reject(new Error('WebSocket 연결 실패'));
      }
    };

    stompClient.activate();
  });

  return connectPromise;
}

export function disconnectStomp() {
  if (client) {
    client.deactivate();
  }
  client = null;
  connectPromise = null;
  isConnected = false;

  activeSubscriptions.forEach((sub) => {
    try {
      sub.unsubscribe();
    } catch {
      // noop
    }
  });
  activeSubscriptions.clear();
}

async function publish(destination, body) {
  const stomp = await connectStomp();
  stomp.publish({
    destination,
    headers: {
      'content-type': 'application/json',
    },
    body: JSON.stringify(body),
  });
}

export async function subscribeUiCommands({ sessionId, onCommand }) {
  const stomp = await connectStomp();

  if (!activeSubscriptions.has('ui-global')) {
    const sub = stomp.subscribe(TOPICS.uiGlobal, (message) => {
      const payload = safeJsonParse(message.body);
      onCommand?.(payload);
    });
    activeSubscriptions.set('ui-global', sub);
  }

  if (sessionId) {
    const key = `ui-session-${sessionId}`;
    if (!activeSubscriptions.has(key)) {
      const sub = stomp.subscribe(TOPICS.uiSession(sessionId), (message) => {
        const payload = safeJsonParse(message.body);
        onCommand?.(payload);
      });
      activeSubscriptions.set(key, sub);
    }
  }
}

export async function subscribeFrontAck({ onAck } = {}) {
  const stomp = await connectStomp();

  if (activeSubscriptions.has('front-ack')) return;

  const sub = stomp.subscribe(TOPICS.frontAck, (message) => {
    const payload = safeJsonParse(message.body);
    onAck?.(payload);
  });

  activeSubscriptions.set('front-ack', sub);
}

export async function sendFrontEvent(action, data = {}) {
  return publish(DESTINATIONS.frontEvents, {
    action,
    data,
    sentAt: new Date().toISOString(),
  });
}

export async function sendUiAck(appliedAction, data = {}) {
  return publish(DESTINATIONS.frontAck, {
    action: 'UI_ACK',
    data: {
      appliedAction,
      ...data,
    },
    sentAt: new Date().toISOString(),
  });
}