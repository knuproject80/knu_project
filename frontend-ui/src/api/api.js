import { Client } from '@stomp/stompjs';

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8080/ws';

/*
 * MCP Client 연동 가이드 기준으로 프론트 이벤트는 /topic/front/events,
 * ACK는 /topic/front/ack 로 보냅니다.
 *
 * Spring 쪽에서 /app prefix를 MessageMapping으로 중계하는 구조라면
 * .env에서 아래 값을 /app/front/events, /app/front/ack 로 바꿔 테스트할 수 있습니다.
 *
 * VITE_FRONT_EVENTS_DESTINATION=/app/front/events
 * VITE_FRONT_ACK_DESTINATION=/app/front/ack
 */
const FRONT_EVENTS_DESTINATION =
  import.meta.env.VITE_FRONT_EVENTS_DESTINATION || '/topic/front/events';
const FRONT_ACK_DESTINATION =
  import.meta.env.VITE_FRONT_ACK_DESTINATION || '/topic/front/ack';

const TOPICS = {
  uiGlobal: import.meta.env.VITE_UI_GLOBAL_TOPIC || '/topic/ui/global',
  uiSession: (sessionId) => `/topic/ui/${sessionId}`,
  frontAck: '/topic/front/ack',
};

const DESTINATIONS = {
  frontEvents: FRONT_EVENTS_DESTINATION,
  frontAck: FRONT_ACK_DESTINATION,
};

let client = null;
let connectPromise = null;
let isConnected = false;

const activeSubscriptions = new Map();
const uiSessionIds = new Set();

let uiCommandHandler = null;
let frontAckHandler = null;

function safeJsonParse(value) {
  try {
    return JSON.parse(value);
  } catch {
    return value;
  }
}

function nowIso() {
  return new Date().toISOString();
}

function getPayloadSessionId(payload) {
  return `${payload?.data?.sessionId || payload?.sessionId || ''}`.trim();
}

function subscribeIfNeeded(key, destination, callback) {
  if (!client || !isConnected || activeSubscriptions.has(key)) return;

  const sub = client.subscribe(destination, callback);
  activeSubscriptions.set(key, sub);
}

function restoreSubscriptions() {
  if (!client || !isConnected) return;

  if (uiCommandHandler) {
    subscribeIfNeeded('ui-global', TOPICS.uiGlobal, handleUiCommandMessage);

    uiSessionIds.forEach((sessionId) => {
      subscribeIfNeeded(
        `ui-session-${sessionId}`,
        TOPICS.uiSession(sessionId),
        handleUiCommandMessage
      );
    });
  }

  if (frontAckHandler) {
    subscribeIfNeeded('front-ack', TOPICS.frontAck, handleFrontAckMessage);
  }
}

function handleUiCommandMessage(message) {
  const payload = safeJsonParse(message.body);
  const incomingSessionId = getPayloadSessionId(payload);

  if (payload?.action === 'SESSION_ASSIGNED' && incomingSessionId) {
    uiSessionIds.add(incomingSessionId);
    restoreSubscriptions();
  }

  uiCommandHandler?.(payload);
}

function handleFrontAckMessage(message) {
  const payload = safeJsonParse(message.body);
  frontAckHandler?.(payload);
}

function ensureClient() {
  if (client) return client;

  client = new Client({
    brokerURL: WS_URL,
    reconnectDelay: 2000,
    heartbeatIncoming: 10000,
    heartbeatOutgoing: 10000,
    debug: () => {},
  });

  client.onConnect = () => {
    isConnected = true;

    /*
     * WebSocket/STOMP가 재연결되면 기존 subscription 객체는 실제로는 끊긴 상태일 수 있다.
     * 그래서 activeSubscriptions를 비우고, 기억해둔 global/session/ack 구독을 다시 건다.
     */
    activeSubscriptions.clear();
    restoreSubscriptions();
  };

  client.onDisconnect = () => {
    isConnected = false;
    connectPromise = null;
    activeSubscriptions.clear();
  };

  client.onWebSocketClose = () => {
    isConnected = false;
    connectPromise = null;
    activeSubscriptions.clear();
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

    const originalOnConnect = stompClient.onConnect;
    const originalOnWebSocketError = stompClient.onWebSocketError;
    const originalOnStompError = stompClient.onStompError;

    const cleanup = () => {
      stompClient.onConnect = originalOnConnect;
      stompClient.onWebSocketError = originalOnWebSocketError;
      stompClient.onStompError = originalOnStompError;
    };

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

    stompClient.onStompError = (frame) => {
      originalOnStompError?.(frame);

      if (!settled) {
        settled = true;
        cleanup();
        reject(new Error(frame.headers?.message || 'STOMP 연결 실패'));
      }
    };

    try {
      stompClient.activate();
    } catch (error) {
      if (!settled) {
        settled = true;
        cleanup();
        reject(error);
      }
    }
  });

  return connectPromise;
}

export function disconnectStomp() {
  activeSubscriptions.forEach((sub) => {
    try {
      sub.unsubscribe();
    } catch {
      // noop
    }
  });

  activeSubscriptions.clear();
  uiSessionIds.clear();

  uiCommandHandler = null;
  frontAckHandler = null;

  if (client) {
    try {
      client.deactivate();
    } catch {
      // noop
    }
  }

  client = null;
  connectPromise = null;
  isConnected = false;
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
  if (onCommand) {
    uiCommandHandler = onCommand;
  }

  const cleanSessionId = `${sessionId || ''}`.trim();
  if (cleanSessionId) {
    uiSessionIds.add(cleanSessionId);
  }

  await connectStomp();
  restoreSubscriptions();
}

export async function subscribeFrontAck({ onAck } = {}) {
  if (onAck) {
    frontAckHandler = onAck;
  }

  await connectStomp();
  restoreSubscriptions();
}

export async function sendFrontEvent(action, data = {}) {
  return publish(DESTINATIONS.frontEvents, {
    action,
    data,
    timestamp: nowIso(),
    sentAt: nowIso(),
  });
}

export async function sendStepChange({ sessionId, step }) {
  const cleanStep = `${step || ''}`.trim();
  const cleanSessionId = `${sessionId || ''}`.trim();

  if (!cleanStep) return false;

  if (!cleanSessionId) {
    console.error('[STEP_CHANGE blocked] sessionId가 없어 STEP_CHANGE를 전송하지 않습니다.');
    return false;
  }

  await sendFrontEvent('STEP_CHANGE', {
    sessionId: cleanSessionId,
    step: cleanStep,
  });

  return true;
}

export async function sendVoiceInput({ text, sessionId, locale = 'ko-KR' }) {
  const cleanText = `${text || ''}`.trim();
  if (!cleanText) return;

  return publish(DESTINATIONS.frontEvents, {
    action: 'VOICE_INPUT',
    text: cleanText,
    target: cleanText,
    confidence: 1,
    data: {
      text: cleanText,
      target: cleanText,
      confidence: 1,
      sessionId,
      locale,
    },
    timestamp: nowIso(),
    sentAt: nowIso(),
  });
}

export async function sendUiAck(appliedAction, data = {}) {
  const payload = {
    action: 'UI_ACK',
    appliedAction,
    commandId: data.commandId,
    sessionId: data.sessionId,
    data: {
      appliedAction,
      ...data,
    },
    timestamp: nowIso(),
    sentAt: nowIso(),
  };

  return publish(DESTINATIONS.frontAck, payload);
}