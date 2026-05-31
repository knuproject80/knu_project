import { Client } from '@stomp/stompjs';

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8080/ws';

/*
 * 기본값은 Spring WebSocket/STOMP 구조에 맞춰 /app 으로 발행합니다.
 * 만약 Spring이 /app/front/events 를 /topic/front/events 로 중계하지 않는 구조라면
 * .env에서 아래처럼 바꿔 테스트할 수 있습니다.
 *
 * VITE_FRONT_EVENTS_DESTINATION=/topic/front/events
 * VITE_FRONT_ACK_DESTINATION=/topic/front/ack
 */
const FRONT_EVENTS_DESTINATION =
  import.meta.env.VITE_FRONT_EVENTS_DESTINATION || '/app/front/events';
const FRONT_ACK_DESTINATION =
  import.meta.env.VITE_FRONT_ACK_DESTINATION || '/app/front/ack';

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

function ensureClient() {
  if (client) return client;

  client = new Client({
    brokerURL: WS_URL,
    reconnectDelay: 2000,
    heartbeatIncoming: 4000,
    heartbeatOutgoing: 4000,
    debug: () => {},
  });

  client.onConnect = () => {
    isConnected = true;
  };

  client.onDisconnect = () => {
    isConnected = false;
    connectPromise = null;
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
    timestamp: nowIso(),
    sentAt: nowIso(),
  });
}

export async function sendStepChange({ sessionId, step }) {
  const cleanStep = `${step || ''}`.trim();
  const cleanSessionId = `${sessionId || 'front-test-session'}`.trim();

  if (!cleanStep) return;

  return sendFrontEvent('STEP_CHANGE', {
    sessionId: cleanSessionId,
    step: cleanStep,
  });
}

export async function sendVoiceInput({ text, sessionId, locale = 'ko-KR' }) {
  const cleanText = `${text || ''}`.trim();
  if (!cleanText) return;

  /*
   * data.text 가 공식 형태입니다.
   * text/target/confidence 를 top-level에도 같이 싣는 이유:
   * 현재 공유된 MCP Client의 intent_analyzer.py가 target/confidence 기반으로 파싱하는 구조라
   * 중간 MCP 구현 상태에서도 디버깅하기 쉽게 하기 위함입니다.
   * 정상 MCP Client가 AI Server에 /classify/service를 호출하는 구조에서는 data.text만 사용하면 됩니다.
   */
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
  return publish(DESTINATIONS.frontAck, {
    action: 'UI_ACK',
    data: {
      appliedAction,
      ...data,
    },
    timestamp: nowIso(),
    sentAt: nowIso(),
  });
}