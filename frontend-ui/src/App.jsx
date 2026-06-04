import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import MainScreen from './components/MainScreen';
import ModeBar from './components/ModeBar';
import ScreenFrame from './components/ScreenFrame';
import ServiceSelect from './components/ServiceSelect';
import VoicePanel from './components/VoicePanel';
import IdentityVerify from './components/IdentityVerify';
import ConfirmFee from './components/ConfirmFee';
import { CopyCountPage, IssueContentPage } from './components/IssueContent';
import {
  TransferConfirm,
  TransferCurrentAddressInfo,
  TransferExtraService,
  TransferHousehold,
  TransferIdentityInfo,
  TransferPreviousInfo,
  TransferReason,
} from './components/TransferReport';
import './styles/App.css';
import { DEFAULT_HISTORY_OPTIONS, LOCAL_SERVICE_CATEGORIES, USER_TYPES } from './data/options';
import {
  connectStomp,
  subscribeFrontAck,
  subscribeUiCommands,
  sendFrontEvent,
  sendStepChange,
  sendUiAck,
  disconnectStomp,
} from './api/api';

const STEP_MAIN = 'main';
const STEP_SERVICE = 'service';
const STEP_VERIFY = 'verify';
const STEP_ISSUE_CONTENT = 'issue_content';
const STEP_COPY_COUNT = 'copy_count';
const STEP_CONFIRM = 'confirm';
const STEP_TRANSFER_IDENTITY = 'transfer_identity';
const STEP_TRANSFER_REASON = 'transfer_reason';
const STEP_TRANSFER_PREVIOUS_SEARCH = 'transfer_previous_search';
const STEP_TRANSFER_CURRENT_ADDRESS = 'transfer_current_address';
const STEP_TRANSFER_HOUSEHOLD = 'transfer_household';
const STEP_TRANSFER_SERVICE = 'transfer_service';
const STEP_TRANSFER_CONFIRM = 'transfer_confirm';

const FEE_PER_COPY = 400;
const RECOGNITION_RESTART_DELAY = 700;
const WAITING_VOICE_GUIDE_TEXT = '다시 말하려면 왼쪽 동그라미 버튼을 눌러 주세요.';
const ACCESSIBILITY_STORAGE_KEY = 'kiosk-accessibility-options';
const FALLBACK_STEP_SESSION_ID = 'front-test-session';

const initialTransferForm = {
  name: '',
  residentFront: '',
  residentBack: '',
  phone1: '010',
  phone2: '',
  phone3: '',
  reason: '',
  prevSido: '대구광역시',
  prevSigungu: '북구',
  prevAddress: '대구광역시 대학로80',
  prevAdminCenter: '대현동',
  movingMembers: ['self'],
  currentBaseAddress: '',
  buildingType: 'ground',
  buildingMainNo: '',
  buildingSubNo: '',
  detailAddress: '',
  householdType: '',
  extraServices: [],
};

const initialForm = {
  flowType: '',
  categoryId: null,
  categoryTitle: '',
  selectedMenuId: null,
  selectedMenuName: '',
  selectedServiceId: '',
  selectedServiceLabel: '',
  residentFront: '',
  residentBack: '',
  issueType: '',
  selectedHistoryOptions: [],
  copyCount: '',
  transfer: initialTransferForm,
};

// MCP Client 테스트 가이드의 STEP_CHANGE key와 현재 프론트 화면을 연결한다.
// STEP_CHANGE payload에는 serviceId를 넣지 않고 sessionId + step만 보낸다.
const STEP_CHANGE_BY_SCREEN = {
  // 프론트에 실제로 존재하는 등본/초본 선택 화면이므로 유지한다.
  // 음성 인식에서 등본/초본이 확정되지 않은 경우 이 단계에서 사용자가 직접 선택한다.
  [STEP_SERVICE]: 'CERTIFICATE_SELECT_PURPOSE',
  [STEP_VERIFY]: 'CERTIFICATE_SELECT_RRN',
  [STEP_ISSUE_CONTENT]: 'CERTIFICATE_SELECT_SCOPE',
  [STEP_COPY_COUNT]: 'CERTIFICATE_SELECT_COUNT',
  [STEP_CONFIRM]: 'CERTIFICATE_CONFIRM',

  // 전입신고는 실제 프론트 화면 수와 1:1로 맞춘다.
  // TransferPreviousInfo 한 페이지 안에 "이전 주소 확인"과 "이사 가는 사람 선택"이 같이 있으므로
  // 별도 MOVEIN_SELECT_MOVING_MEMBERS 단계는 보내지 않는다.
  [STEP_TRANSFER_IDENTITY]: 'MOVEIN_INPUT_BASIC_INFO',
  [STEP_TRANSFER_REASON]: 'MOVEIN_SELECT_REASON',
  [STEP_TRANSFER_PREVIOUS_SEARCH]: 'MOVEIN_INPUT_PREV_ADDRESS',
  [STEP_TRANSFER_CURRENT_ADDRESS]: 'MOVEIN_INPUT_NEW_ADDRESS',
  [STEP_TRANSFER_HOUSEHOLD]: 'MOVEIN_SELECT_HOUSEHOLD',
  [STEP_TRANSFER_SERVICE]: 'MOVEIN_SELECT_EXTRA_SERVICE',
  [STEP_TRANSFER_CONFIRM]: 'MOVEIN_CONFIRM',
};

const SCREEN_BY_STEP_CHANGE = {
  CERTIFICATE_SELECT_PURPOSE: STEP_SERVICE,
  CERTIFICATE_SELECT_RRN: STEP_VERIFY,
  CERTIFICATE_SELECT_SCOPE: STEP_ISSUE_CONTENT,
  CERTIFICATE_SELECT_COUNT: STEP_COPY_COUNT,
  CERTIFICATE_CONFIRM: STEP_CONFIRM,

  MOVEIN_INPUT_BASIC_INFO: STEP_TRANSFER_IDENTITY,
  MOVEIN_SELECT_REASON: STEP_TRANSFER_REASON,
  MOVEIN_INPUT_PREV_ADDRESS: STEP_TRANSFER_PREVIOUS_SEARCH,
  MOVEIN_INPUT_NEW_ADDRESS: STEP_TRANSFER_CURRENT_ADDRESS,
  MOVEIN_SELECT_HOUSEHOLD: STEP_TRANSFER_HOUSEHOLD,
  MOVEIN_SELECT_EXTRA_SERVICE: STEP_TRANSFER_SERVICE,
  MOVEIN_CONFIRM: STEP_TRANSFER_CONFIRM,

  // MCP Client가 예전 step을 내려줄 때를 대비한 호환용 매핑
  MOVEIN_INPUT_MEMBERS: STEP_TRANSFER_HOUSEHOLD,
};

const NEXT_SCREEN_BY_SCREEN = {
  [STEP_SERVICE]: STEP_VERIFY,
  [STEP_VERIFY]: STEP_ISSUE_CONTENT,
  [STEP_ISSUE_CONTENT]: STEP_COPY_COUNT,
  [STEP_COPY_COUNT]: STEP_CONFIRM,
  [STEP_TRANSFER_IDENTITY]: STEP_TRANSFER_REASON,
  [STEP_TRANSFER_REASON]: STEP_TRANSFER_PREVIOUS_SEARCH,
  [STEP_TRANSFER_PREVIOUS_SEARCH]: STEP_TRANSFER_CURRENT_ADDRESS,
  [STEP_TRANSFER_CURRENT_ADDRESS]: STEP_TRANSFER_HOUSEHOLD,
  [STEP_TRANSFER_HOUSEHOLD]: STEP_TRANSFER_SERVICE,
  [STEP_TRANSFER_SERVICE]: STEP_TRANSFER_CONFIRM,
};

function loadInitialAccessibility() {
  // 새로고침하면 항상 기본 모드에서 시작한다.
  // 접근성 모드는 현재 실행 중에만 적용하고 localStorage에 저장하지 않는다.
  return { ...USER_TYPES.NORMAL };
}
function normalizeAccessibility(accessibility) {
  return {
    ...accessibility,
    fontSize: accessibility.largeFont ? 24 : 16,
  };
}

export default function App() {
  const [screen, setScreen] = useState(STEP_MAIN);
  const [categories] = useState(LOCAL_SERVICE_CATEGORIES);
  const [sessionId, setSessionId] = useState(FALLBACK_STEP_SESSION_ID);
  const [accessibility, setAccessibility] = useState(loadInitialAccessibility);
  const [statusMessage, setStatusMessage] = useState('');
  const [submittedApplicationNo, setSubmittedApplicationNo] = useState('');
  const [form, setForm] = useState(initialForm);

  const submitResetTimerRef = useRef(null);
  const sessionIdRef = useRef(FALLBACK_STEP_SESSION_ID);
  const screenRef = useRef(STEP_MAIN);
  const accessibilityRef = useRef(accessibility);
  const autoAdvanceLockRef = useRef(false);
  const recognitionRef = useRef(null);
  const restartTimerRef = useRef(null);
  const shouldListenRef = useRef(false);
  const speechUnlockedRef = useRef(false);
  const preserveVoicePanelTextRef = useRef(false);

  const [voicePanelVisible, setVoicePanelVisible] = useState(false);
  const [voiceUi, setVoiceUi] = useState({
    listening: false,
    supported: true,
    transcript: '',
    guideText: '음성안내 버튼을 누르면 마이크 입력을 받을 수 있습니다.',
    error: '',
  });

  useEffect(() => {
    sessionIdRef.current = sessionId;
  }, [sessionId]);

  useEffect(() => {
    screenRef.current = screen;
  }, [screen]);

  useEffect(() => {
    accessibilityRef.current = accessibility;
  }, [accessibility]);

  useEffect(() => {
    if (!statusMessage) return undefined;

    const timer = window.setTimeout(() => {
      setStatusMessage('');
    }, 5000);

    return () => {
      window.clearTimeout(timer);
    };
  }, [statusMessage]);

  const clearSubmitResetTimer = () => {
    if (submitResetTimerRef.current) {
      clearTimeout(submitResetTimerRef.current);
      submitResetTimerRef.current = null;
    }
  };

  const safeSendFrontEvent = useCallback(async (action, data = {}) => {
    try {
      await sendFrontEvent(action, data);
      return true;
    } catch (error) {
      // Spring/MCP가 꺼져 있어도 로컬 화면 이동과 버튼 클릭은 막지 않는다.
      console.warn(`[front-event skipped] ${action}`, error);
      return false;
    }
  }, []);

  //
  useEffect(() => {
  if (!import.meta.env.DEV) return undefined;

  window.__sendFrontEventForTest = sendFrontEvent;
  window.__sendStepChangeForTest = sendStepChange;

  return () => {
    delete window.__sendFrontEventForTest;
    delete window.__sendStepChangeForTest;
  };
}, []);
  //
  const safeSendStepChange = useCallback(async (nextScreen, nextSessionId = '') => {
    const step = STEP_CHANGE_BY_SCREEN[nextScreen];
    const activeSessionId = `${nextSessionId || sessionIdRef.current || FALLBACK_STEP_SESSION_ID}`.trim();

    if (!step) return false;

    try {
      await sendStepChange({
        sessionId: activeSessionId,
        step,
      });
      return true;
    } catch (error) {
      // STEP_CHANGE 실패가 화면 이동 자체를 막으면 테스트/시연이 더 어려워지므로 경고만 남긴다.
      console.warn('[front-event skipped] STEP_CHANGE', error);
      return false;
    }
  }, []);

  const unlockSpeechSynthesis = useCallback(() => {
    if (
      speechUnlockedRef.current ||
      typeof window === 'undefined' ||
      !('speechSynthesis' in window) ||
      typeof SpeechSynthesisUtterance === 'undefined'
    ) {
      return;
    }

    try {
      const synth = window.speechSynthesis;
      const utterance = new SpeechSynthesisUtterance(' ');
      utterance.volume = 0;
      utterance.lang = 'ko-KR';

      synth.cancel();
      synth.speak(utterance);
      synth.cancel();
      speechUnlockedRef.current = true;
    } catch {
      // 브라우저가 아직 음성 엔진을 열지 못하면 실제 안내 시도 때 다시 처리한다.
    }
  }, []);

  const speakGuide = useCallback((text, lang = 'ko-KR') => {
    const cleanText = `${text || ''}`.trim();

    if (
      !cleanText ||
      typeof window === 'undefined' ||
      !('speechSynthesis' in window) ||
      typeof SpeechSynthesisUtterance === 'undefined'
    ) {
      return Promise.resolve(false);
    }

    return new Promise((resolve) => {
      const synth = window.speechSynthesis;
      const utterance = new SpeechSynthesisUtterance(cleanText);
      let started = false;
      let settled = false;

      const finish = (result) => {
        if (settled) return;
        settled = true;
        resolve(result);
      };

      const applyKoreanVoice = () => {
        const voices = synth.getVoices?.() || [];
        const normalizedLang = `${lang || 'ko-KR'}`.toLowerCase();
        const langPrefix = normalizedLang.split('-')[0];

        const matchedVoice =
          voices.find((voice) => `${voice.lang || ''}`.toLowerCase() === normalizedLang) ||
          voices.find((voice) => `${voice.lang || ''}`.toLowerCase().startsWith('ko')) ||
          voices.find((voice) => `${voice.lang || ''}`.toLowerCase().startsWith(langPrefix));

        if (matchedVoice) {
          utterance.voice = matchedVoice;
        }
      };

      const startSpeak = () => {
        if (started) return;
        started = true;

        try {
          applyKoreanVoice();
          utterance.lang = lang || 'ko-KR';
          utterance.rate = 0.95;
          utterance.pitch = 1;
          utterance.volume = 1;
          utterance.onend = () => finish(true);
          utterance.onerror = (event) => {
            console.warn('[voice-guide skipped]', event.error || event);
            finish(false);
          };

          synth.cancel();

          window.setTimeout(() => {
            try {
              synth.speak(utterance);
              synth.resume?.();
            } catch (error) {
              console.warn('[voice-guide skipped]', error);
              finish(false);
            }
          }, 60);
        } catch (error) {
          console.warn('[voice-guide skipped]', error);
          finish(false);
        }
      };

      if ((synth.getVoices?.() || []).length > 0) {
        startSpeak();
      } else {
        synth.onvoiceschanged = () => {
          synth.onvoiceschanged = null;
          startSpeak();
        };
        window.setTimeout(startSpeak, 300);
      }

      // 브라우저 정책/음성 엔진 문제로 onend가 오지 않는 경우에도 UI 흐름이 멈추지 않게 한다.
      window.setTimeout(() => finish(false), Math.max(4500, cleanText.length * 180));
    });
  }, []);

  const getScreenFromStepKey = useCallback((stepKey) => {
    return SCREEN_BY_STEP_CHANGE[stepKey] || null;
  }, []);

  const applyPrefilledValue = useCallback((targetScreen, value) => {
    if (value === undefined || value === null) return;

    setForm((prev) => {
      if (targetScreen === STEP_SERVICE) {
        const rawValue = typeof value === 'object' ? value : {};
        const text = String(rawValue.label || rawValue.serviceName || rawValue.serviceId || value || '').toUpperCase();

        if (text.includes('ABSTRACT') || text.includes('초본')) {
          return {
            ...prev,
            selectedServiceId: rawValue.id || rawValue.serviceId || 'resident-abstract',
            selectedServiceLabel: rawValue.label || rawValue.serviceName || '주민등록초본 발급',
          };
        }

        if (text.includes('COPY') || text.includes('등본')) {
          return {
            ...prev,
            selectedServiceId: rawValue.id || rawValue.serviceId || 'resident-copy',
            selectedServiceLabel: rawValue.label || rawValue.serviceName || '주민등록등본 발급',
          };
        }
      }

      if (targetScreen === STEP_ISSUE_CONTENT) {
        const text = String(value).toLowerCase();

        if (text.includes('all') || text.includes('전체')) {
          return {
            ...prev,
            issueType: 'all',
            selectedHistoryOptions: [],
          };
        }

        if (text.includes('select') || text.includes('선택')) {
          return {
            ...prev,
            issueType: 'select',
          };
        }
      }

      if (targetScreen === STEP_COPY_COUNT) {
        const nextCopyCount = String(value).replace(/[^0-9]/g, '').slice(0, 2);

        if (!nextCopyCount || Number(nextCopyCount) < 1) return prev;

        return {
          ...prev,
          copyCount: nextCopyCount,
        };
      }

      return prev;
    });
  }, []);

  const advanceAutoFilledStep = useCallback(async (targetScreen, nextSessionId = '') => {
    if (autoAdvanceLockRef.current) return false;

    const currentScreen = targetScreen || screenRef.current;
    const nextScreen = NEXT_SCREEN_BY_SCREEN[currentScreen];

    if (!nextScreen) return false;

    autoAdvanceLockRef.current = true;

    try {
      const activeSessionId = nextSessionId || sessionIdRef.current || FALLBACK_STEP_SESSION_ID;

      screenRef.current = nextScreen;
      setScreen(nextScreen);
      await safeSendStepChange(nextScreen, activeSessionId);
      return true;
    } finally {
      window.setTimeout(() => {
        autoAdvanceLockRef.current = false;
      }, 0);
    }
  }, [safeSendStepChange]);

  const stopVoiceRecognition = useCallback(() => {
    shouldListenRef.current = false;

    if (restartTimerRef.current) {
      clearTimeout(restartTimerRef.current);
      restartTimerRef.current = null;
    }

    const recognition = recognitionRef.current;
    if (recognition) {
      try {
        recognition.onend = null;
        recognition.stop();
      } catch {
        // 이미 중지된 상태면 무시
      }
    }

    setVoiceUi((prev) => ({
      ...prev,
      listening: false,
    }));
  }, []);

  const sendVoiceText = useCallback(async (text) => {
    const trimmed = text.trim();
    if (!trimmed) return;

    stopVoiceRecognition();

    setVoiceUi((prev) => ({
      ...prev,
      listening: false,
      transcript: trimmed,
      error: '',
      guideText: WAITING_VOICE_GUIDE_TEXT,
    }));

    safeSendFrontEvent('VOICE_INPUT', {
      text: trimmed,
      sessionId: sessionIdRef.current,
      locale: 'ko-KR',
    });
  }, [safeSendFrontEvent, stopVoiceRecognition]);

  const startVoiceRecognition = useCallback(() => {
    if (typeof window === 'undefined') return;

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setVoicePanelVisible(true);
      setVoiceUi((prev) => ({
        ...prev,
        supported: false,
        listening: false,
        error: '이 브라우저에서는 음성인식을 지원하지 않습니다. Chrome에서 실행해 주세요.',
      }));
      return;
    }

    stopVoiceRecognition();

    const recognition = new SpeechRecognition();
    recognition.lang = 'ko-KR';
    recognition.interimResults = true;
    recognition.continuous = true;
    recognition.maxAlternatives = 1;
    recognitionRef.current = recognition;
    shouldListenRef.current = true;

    recognition.onstart = () => {
      const preservePanelText = preserveVoicePanelTextRef.current;
      preserveVoicePanelTextRef.current = false;

      setVoicePanelVisible(true);
      setVoiceUi((prev) => ({
        ...prev,
        supported: true,
        listening: true,
        error: '',
        guideText: preservePanelText
          ? prev.guideText
          : '듣고 있습니다. 원하는 서비스를 말씀해 주세요.',
      }));
    };

    recognition.onresult = (event) => {
      let interim = '';
      let finalText = '';

      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const result = event.results[i];
        const text = result[0]?.transcript || '';
        if (result.isFinal) finalText += text;
        else interim += text;
      }

      const shownText = (finalText || interim).trim();
      if (shownText) {
        setVoiceUi((prev) => ({
          ...prev,
          transcript: shownText,
        }));
      }

      if (finalText.trim()) {
        sendVoiceText(finalText);
      }
    };

    recognition.onerror = (event) => {
      const messageMap = {
        'not-allowed': '마이크 권한이 허용되지 않았습니다.',
        'no-speech': '음성이 감지되지 않았습니다.',
        network: '음성인식 네트워크 오류가 발생했습니다.',
      };

      if (event.error === 'no-speech') {
        shouldListenRef.current = false;

        if (restartTimerRef.current) {
          clearTimeout(restartTimerRef.current);
          restartTimerRef.current = null;
        }

        setVoiceUi((prev) => ({
          ...prev,
          listening: false,
          error: messageMap[event.error],
          guideText: WAITING_VOICE_GUIDE_TEXT,
        }));

        return;
      }

      setVoiceUi((prev) => ({
        ...prev,
        listening: false,
        error: messageMap[event.error] || `음성인식 오류: ${event.error}`,
      }));
    };

    recognition.onend = () => {
      setVoiceUi((prev) => ({
        ...prev,
        listening: false,
      }));

      if (shouldListenRef.current && accessibilityRef.current.voiceMode) {
        restartTimerRef.current = setTimeout(() => {
          try {
            recognition.start();
          } catch {
            // 이미 시작 중이면 무시
          }
        }, RECOGNITION_RESTART_DELAY);
      }
    };

    try {
      recognition.start();
    } catch {
      setVoiceUi((prev) => ({
        ...prev,
        listening: false,
        error: '음성인식을 시작하지 못했습니다. 잠시 후 다시 눌러 주세요.',
      }));
    }
  }, [sendVoiceText, stopVoiceRecognition]);

  const playVoiceGuide = useCallback(async (text, lang = 'ko-KR') => {
    const cleanText = `${text || ''}`.trim();
    if (!cleanText) return false;

    const shouldRestartRecognition =
      Boolean(accessibilityRef.current.voiceMode) &&
      Boolean(recognitionRef.current) &&
      Boolean(shouldListenRef.current);

    if (shouldRestartRecognition) {
      stopVoiceRecognition();
    }

    const played = await speakGuide(cleanText, lang);

    if (shouldRestartRecognition && accessibilityRef.current.voiceMode) {
      window.setTimeout(() => {
        if (accessibilityRef.current.voiceMode) {
          // TTS 뒤에 STT를 다시 켜더라도, 패널 문구/인식된 말은 그대로 유지한다.
          preserveVoicePanelTextRef.current = true;
          startVoiceRecognition();
        }
      }, 250);
    }

    return played;
  }, [speakGuide, startVoiceRecognition, stopVoiceRecognition]);

  const turnOffVoiceMode = useCallback(async () => {
    stopVoiceRecognition();
    setVoicePanelVisible(false);
    setVoiceUi((prev) => ({
      ...prev,
      transcript: '',
      error: '',
      guideText: '음성안내 버튼을 누르면 마이크 입력을 받을 수 있습니다.',
    }));

    const normalized = normalizeAccessibility({
      ...accessibilityRef.current,
      voiceMode: false,
    });

    setAccessibility(normalized);

    safeSendFrontEvent('TOGGLE_ACCESSIBILITY', {
      sessionId: sessionIdRef.current,
      actionKey: 'voiceMode',
      accessibility: normalized,
    });
  }, [safeSendFrontEvent, stopVoiceRecognition]);

  useEffect(() => {
    let mounted = true;

    async function bootstrap() {
      try {
        await connectStomp();

        await subscribeFrontAck({
          onAck: (payload) => {
            console.log('front ack:', payload);
          },
        });

        // 앱 시작 알림만 보냄
        safeSendFrontEvent('FRONT_READY', { ui: 'kiosk' });

        // 세션/유휴시간/페이지 이동은 서버 또는 MCP Client가 내려주는 명령을 따르는 구조로 유지
        await subscribeUiCommands({
          sessionId: FALLBACK_STEP_SESSION_ID,
          onCommand: async function handleUiCommand(message) {
            if (!mounted || !message) return;

            const action = message.action;
            const data = message.data || {};

            const subscribeSessionTopic = async (rawSessionId) => {
              const nextSessionId = `${rawSessionId || ''}`.trim();
              if (!nextSessionId) return '';

              // MCP가 새 세션을 발급한 뒤 /topic/ui/{sessionId}로 화면전환/음성안내를 보내면
              // 프론트가 그 토픽을 구독하고 있어야 명령을 받을 수 있다.
              // subscribeUiCommands 내부에서 같은 sessionId는 중복 구독하지 않는다.
              sessionIdRef.current = nextSessionId;
              setSessionId(nextSessionId);
              await subscribeUiCommands({
                sessionId: nextSessionId,
                onCommand: handleUiCommand,
              });

              return nextSessionId;
            };

            const incomingCommandSessionId = data.sessionId || message.sessionId;
            if (incomingCommandSessionId) {
              await subscribeSessionTopic(incomingCommandSessionId);
            }

            if (action === 'SESSION_ASSIGNED') {
              const assignedSessionId = await subscribeSessionTopic(
                data.sessionId || message.sessionId
              );

              await sendUiAck('SESSION_ASSIGNED', {
                sessionId: assignedSessionId || sessionIdRef.current || FALLBACK_STEP_SESSION_ID,
                commandId: message.commandId,
              });
              return;
            }

            if (action === 'ADAPT_UI') {
              const incomingAccessibility = data.accessibility || data.settings;

              if (incomingAccessibility) {
                setAccessibility((prev) =>
                  normalizeAccessibility({
                    ...prev,
                    ...incomingAccessibility,
                    fontSize: Number.parseInt(incomingAccessibility.fontSize, 10) || prev.fontSize,
                  })
                );
              }
              await sendUiAck('ADAPT_UI', {
                sessionId: data.sessionId || sessionIdRef.current || FALLBACK_STEP_SESSION_ID,
                commandId: message.commandId,
              });
              return;
            }

            if (action === 'MOVE_PAGE') {
              // TC-FE-19 대응:
              // MOVE_PAGE payload에 명시적인 sessionId가 없으면 STEP_CHANGE를 보내지 않는다.
              // 단, 화면 이동과 UI_ACK는 유지해서 Mock/오류 케이스에서도 UI가 멈추지 않게 한다.
              const commandSessionId = `${data.sessionId || message.sessionId || ''}`.trim();
              const ackSessionId = commandSessionId || sessionIdRef.current || FALLBACK_STEP_SESSION_ID;

              if (commandSessionId) {
                sessionIdRef.current = commandSessionId;
                setSessionId(commandSessionId);
              }

              const rawTarget = data.page || data.pageId || data.serviceId;
              let targetPage = rawTarget;

              if (rawTarget === 101 || rawTarget === '101' || rawTarget === 'MOVE_IN_REPORT') {
                targetPage = STEP_TRANSFER_IDENTITY;
                setForm((prev) => ({
                  ...prev,
                  flowType: 'transfer',
                  categoryId: 'personal',
                  categoryTitle: '민원신청',
                  selectedMenuId: 'p1',
                  selectedMenuName: '전입신고',
                  selectedServiceId: 'p1',
                  selectedServiceLabel: '전입신고',
                  transfer: initialTransferForm,
                }));
              }

              if (rawTarget === 102 || rawTarget === '102' || rawTarget === 'RESIDENT_REGISTRATION_COPY') {
                targetPage = STEP_SERVICE;
                setForm((prev) => ({
                  ...prev,
                  flowType: 'resident',
                  categoryId: 'certificate',
                  categoryTitle: '증명서발급',
                  selectedMenuId: 'resident-copy',
                  selectedMenuName: '주민등록등본(초본)',
                }));
              }

              const allowedPages = [
                STEP_MAIN,
                STEP_SERVICE,
                STEP_VERIFY,
                STEP_ISSUE_CONTENT,
                STEP_COPY_COUNT,
                STEP_CONFIRM,
                STEP_TRANSFER_IDENTITY,
                STEP_TRANSFER_REASON,
                STEP_TRANSFER_PREVIOUS_SEARCH,
                STEP_TRANSFER_CURRENT_ADDRESS,
                STEP_TRANSFER_HOUSEHOLD,
                STEP_TRANSFER_SERVICE,
                STEP_TRANSFER_CONFIRM,
              ];

              if (allowedPages.includes(targetPage)) {
                screenRef.current = targetPage;
                setScreen(targetPage);

                if (commandSessionId) {
                  safeSendStepChange(targetPage, commandSessionId);
                } else {
                  console.error('[STEP_CHANGE skipped] MOVE_PAGE command has no sessionId:', message);
                }
              }

              await sendUiAck('MOVE_PAGE', {
                sessionId: ackSessionId,
                page: targetPage,
                commandId: message.commandId,
              });
              return;
            }

            if (action === 'VOICE_GUIDE') {
              // MCP가 text를 data 안에 넣어 보내는 경우도 있고,
              // 로그처럼 text/context/userType을 top-level에 바로 넣어 보내는 경우도 있다.
              const guideText = `${data.autoAdvanceGuide || data.guideText || data.text || data.answer || message.autoAdvanceGuide || message.guideText || message.text || message.answer || ''}`.trim();
              const guideLang = data.lang || data.locale || message.lang || message.locale || 'ko-KR';
              const isAutoAdvance = data.autoAdvance === true || data.autoAdvance === 'true' || message.autoAdvance === true || message.autoAdvance === 'true';

              if (isAutoAdvance) {
                const stepKey =
                  data.step ||
                  data.stepKey ||
                  data.context ||
                  message.step ||
                  message.stepKey ||
                  message.context ||
                  STEP_CHANGE_BY_SCREEN[screenRef.current];

                const targetScreen = getScreenFromStepKey(stepKey) || screenRef.current;
                const activeSessionId =
                  data.sessionId || message.sessionId || sessionIdRef.current || FALLBACK_STEP_SESSION_ID;

                applyPrefilledValue(targetScreen, data.prefilledValue ?? message.prefilledValue);

                // VOICE_GUIDE는 TTS로만 재생한다.
                // 이 작은 패널은 STT 상태/인식 결과 표시용이므로 guideText/visible을 건드리지 않는다.
                if (guideText) {
                  await playVoiceGuide(guideText, guideLang);
                } else {
                  console.warn('[voice-guide skipped] VOICE_GUIDE text 없음:', message);
                }

                await advanceAutoFilledStep(targetScreen, activeSessionId);
                return;
              }

              // VOICE_GUIDE는 TTS로만 재생한다.
              // 이 작은 패널은 STT 상태/인식 결과 표시용이므로 guideText/visible을 건드리지 않는다.
              if (guideText) {
                await playVoiceGuide(guideText, guideLang);
              } else {
                console.warn('[voice-guide skipped] VOICE_GUIDE text 없음:', message);
              }
              return;
            }

            if (action === 'GO_HOME') {
              clearSubmitResetTimer();
              setForm(initialForm);
              setSubmittedApplicationNo('');
              setStatusMessage('');
              stopVoiceRecognition();
              setVoicePanelVisible(false);
              setAccessibility({ ...USER_TYPES.NORMAL });
              setScreen(STEP_MAIN);

              await sendUiAck('GO_HOME', {
                sessionId: data.sessionId || sessionIdRef.current || FALLBACK_STEP_SESSION_ID,
                commandId: message.commandId,
              });
              return;
            }

            if (action === 'SESSION_EXPIRED') {
              clearSubmitResetTimer();
              setForm(initialForm);
              setSubmittedApplicationNo('');
              setStatusMessage('세션이 만료되었습니다. 처음 화면으로 이동합니다.');
              stopVoiceRecognition();
              setVoicePanelVisible(false);
              setAccessibility({ ...USER_TYPES.NORMAL });
              setScreen(STEP_MAIN);

              await sendUiAck('SESSION_EXPIRED', {
                sessionId: data.sessionId || sessionIdRef.current || FALLBACK_STEP_SESSION_ID,
                commandId: message.commandId,
              });
              return;
            }

            if (action === 'IDLE_WARNING') {
              setStatusMessage(data.message || '잠시 후 처음 화면으로 돌아갑니다.');
              return;
            }

            if (action === 'SUBMIT_RESULT') {
              setSubmittedApplicationNo(data.applicationNo || '');
              setStatusMessage(
                data.message || `접수가 완료되었습니다. 신청번호: ${data.applicationNo || '확인 필요'}`
              );

              // 화면 전환은 MCP Client가 내려주는 GO_HOME 명령을 따른다.
              // 프론트 자체 2.5초 자동 홈 이동은 STEP/세션 흐름을 꼬이게 만들 수 있어 제거한다.
              clearSubmitResetTimer();
            }
          },
        });
      } catch (error) {
        console.error(error);
        // 서버 연결 실패는 버튼 동작을 막지 않는다.
      }
    }

    bootstrap();

    return () => {
      mounted = false;
      clearSubmitResetTimer();
      stopVoiceRecognition();
      disconnectStomp();
    };
  }, [advanceAutoFilledStep, applyPrefilledValue, getScreenFromStepKey, playVoiceGuide, safeSendFrontEvent, safeSendStepChange, stopVoiceRecognition]);

  const confirmSummary = useMemo(() => {
    const serviceName = form.selectedServiceLabel || form.selectedMenuName || '주민등록등본 발급';
    const issueTypeLabel = form.issueType === 'all' ? '전체발급' : '선택발급';
    const residentNumber = `${form.residentFront || ''}-${form.residentBack ? '●'.repeat(form.residentBack.length) : ''}`;

    return {
      serviceName,
      issueTypeLabel,
      residentNumber,
      selectedOptions: form.issueType === 'select' ? form.selectedHistoryOptions : [],
      copyCount: form.copyCount || '1',
    };
  }, [form]);

  const totalFee = (Number(form.copyCount) || 0) * FEE_PER_COPY;

  const resetToHome = async () => {
    clearSubmitResetTimer();
    const activeSessionId = sessionId || sessionIdRef.current || FALLBACK_STEP_SESSION_ID;

    // 중간에 메인으로 나가는 것은 취소 흐름이므로 MCP가 GO_HOME을 내려줄 수 있게 USER_CANCEL을 먼저 보낸다.
    await safeSendFrontEvent('USER_CANCEL', {
      sessionId: activeSessionId,
    });

    setForm(initialForm);
    setSubmittedApplicationNo('');
    setStatusMessage('');
    stopVoiceRecognition();
    setVoicePanelVisible(false);
    setVoiceUi((prev) => ({
      ...prev,
      transcript: '',
      error: '',
      guideText: '음성안내 버튼을 누르면 마이크 입력을 받을 수 있습니다.',
    }));
    setAccessibility({ ...USER_TYPES.NORMAL });
    setScreen(STEP_MAIN);
  };

  const handleAccessibilityAction = async (actionKey) => {
    unlockSpeechSynthesis();
    const nextAccessibility = { ...accessibility };

    if (actionKey === 'voiceMode') {
      nextAccessibility.voiceMode = !nextAccessibility.voiceMode;
    } else if (actionKey === 'largeFont') {
      nextAccessibility.largeFont = !nextAccessibility.largeFont;
    } else if (actionKey === 'lowScreenMode') {
      nextAccessibility.lowScreenMode = !nextAccessibility.lowScreenMode;
    } else if (actionKey === 'highContrast') {
      nextAccessibility.highContrast = !nextAccessibility.highContrast;
    }

    const normalized = normalizeAccessibility(nextAccessibility);
    setAccessibility(normalized);

    if (actionKey === 'voiceMode') {
      if (normalized.voiceMode) {
        // 음성모드를 새로 켤 때마다 이전 인식 문장과 오류를 초기화한다.
        setVoicePanelVisible(true);
        setVoiceUi((prev) => ({
          ...prev,
          transcript: '',
          guideText: '듣고 있습니다. 원하는 서비스를 말씀해 주세요.',
          error: '',
        }));
        startVoiceRecognition();
      } else {
        stopVoiceRecognition();
        setVoicePanelVisible(false);
        setVoiceUi((prev) => ({
          ...prev,
          transcript: '',
          error: '',
          guideText: '음성안내 버튼을 누르면 마이크 입력을 받을 수 있습니다.',
        }));
      }
    }

    safeSendFrontEvent('TOGGLE_ACCESSIBILITY', {
      sessionId,
      actionKey,
      accessibility: normalized,
    });
  };

  const handleMainServiceClick = async (item) => {
    unlockSpeechSynthesis();
    const activeSessionId = sessionId || sessionIdRef.current || FALLBACK_STEP_SESSION_ID;

    safeSendFrontEvent('USER_TOUCH', {
      sessionId: activeSessionId,
      action: 'SELECT_MAIN_MENU',
      menuId: item.id,
    });

    if (item.type === 'resident') {
      setForm((prev) => ({
        ...prev,
        flowType: 'resident',
        categoryId: 'certificate',
        categoryTitle: '증명서발급',
        selectedMenuId: item.id,
        selectedMenuName: item.name,
      }));

      screenRef.current = STEP_SERVICE;
      setScreen(STEP_SERVICE);
      await safeSendStepChange(STEP_SERVICE, activeSessionId);
      return;
    }

    if (item.type === 'move-report') {
      setForm((prev) => ({
        ...prev,
        flowType: 'transfer',
        categoryId: 'personal',
        categoryTitle: '민원신청',
        selectedMenuId: item.id,
        selectedMenuName: item.name,
        selectedServiceId: item.id,
        selectedServiceLabel: item.name,
        transfer: initialTransferForm,
      }));
      setStatusMessage('');

      screenRef.current = STEP_TRANSFER_IDENTITY;
      setScreen(STEP_TRANSFER_IDENTITY);
      await safeSendStepChange(STEP_TRANSFER_IDENTITY, activeSessionId);
      return;
    }

    setStatusMessage('현재 예시는 주민등록등본/초본과 전입신고 흐름만 구현되어 있습니다.');
  };

  const handleSelectService = async (service) => {
    unlockSpeechSynthesis();
    setForm((prev) => ({
      ...prev,
      selectedServiceId: service.id,
      selectedServiceLabel: service.label,
    }));

    safeSendFrontEvent('USER_TOUCH', {
      sessionId,
      action: 'SELECT_SERVICE_TYPE',
      serviceId: service.id,
    });
  };

  const handleResidentKeypad = async (key) => {
    setForm((prev) => {
      const frontFull = prev.residentFront.length >= 6;

      if (key === 'X') {
        if (prev.residentBack.length > 0) {
          return { ...prev, residentBack: prev.residentBack.slice(0, -1) };
        }
        return { ...prev, residentFront: prev.residentFront.slice(0, -1) };
      }

      if (!/^\d$/.test(key)) return prev;
      if (!frontFull) {
        return {
          ...prev,
          residentFront: `${prev.residentFront}${key}`.slice(0, 6),
        };
      }

      return {
        ...prev,
        residentBack: `${prev.residentBack}${key}`.slice(0, 7),
      };
    });

    safeSendFrontEvent('USER_TOUCH', {
      sessionId,
      action: 'INPUT_RESIDENT_NUMBER',
      key,
    });
  };

  const handleCopyCountKeypad = async (key) => {
    setForm((prev) => {
      if (key === 'X') {
        return { ...prev, copyCount: prev.copyCount.slice(0, -1) };
      }
      if (!/^\d$/.test(key)) return prev;

      const next = `${prev.copyCount}${key}`.replace(/^0+(?=\d)/, '').slice(0, 2);
      return { ...prev, copyCount: next };
    });

    safeSendFrontEvent('USER_TOUCH', {
      sessionId,
      action: 'INPUT_COPY_COUNT',
      key,
    });
  };

  const handleTransferResidentKeypad = async (key) => {
    setForm((prev) => {
      const frontFull = prev.transfer.residentFront.length >= 6;

      if (key === 'X') {
        if (prev.transfer.residentBack.length > 0) {
          return {
            ...prev,
            transfer: {
              ...prev.transfer,
              residentBack: prev.transfer.residentBack.slice(0, -1),
            },
          };
        }
        return {
          ...prev,
          transfer: {
            ...prev.transfer,
            residentFront: prev.transfer.residentFront.slice(0, -1),
          },
        };
      }

      if (!/^\d$/.test(key)) return prev;

      if (!frontFull) {
        return {
          ...prev,
          transfer: {
            ...prev.transfer,
            residentFront: `${prev.transfer.residentFront}${key}`.slice(0, 6),
          },
        };
      }

      return {
        ...prev,
        transfer: {
          ...prev.transfer,
          residentBack: `${prev.transfer.residentBack}${key}`.slice(0, 7),
        },
      };
    });

    safeSendFrontEvent('USER_TOUCH', {
      sessionId,
      action: 'INPUT_TRANSFER_RESIDENT_NUMBER',
      key,
    });
  };

  const handlePrev = async () => {
    unlockSpeechSynthesis();
    const prevMap = {
      [STEP_SERVICE]: STEP_MAIN,
      [STEP_VERIFY]: STEP_SERVICE,
      [STEP_ISSUE_CONTENT]: STEP_VERIFY,
      [STEP_COPY_COUNT]: STEP_ISSUE_CONTENT,
      [STEP_CONFIRM]: STEP_COPY_COUNT,
      [STEP_TRANSFER_IDENTITY]: STEP_MAIN,
      [STEP_TRANSFER_REASON]: STEP_TRANSFER_IDENTITY,
      [STEP_TRANSFER_PREVIOUS_SEARCH]: STEP_TRANSFER_REASON,
      [STEP_TRANSFER_CURRENT_ADDRESS]: STEP_TRANSFER_PREVIOUS_SEARCH,
      [STEP_TRANSFER_HOUSEHOLD]: STEP_TRANSFER_CURRENT_ADDRESS,
      [STEP_TRANSFER_SERVICE]: STEP_TRANSFER_HOUSEHOLD,
      [STEP_TRANSFER_CONFIRM]: STEP_TRANSFER_SERVICE,
    };

    const prev = prevMap[screen];
    if (!prev) return;

    /*
     * 이전 버튼은 서비스 취소가 아니라 단순 화면 이동이다.
     * USER_CANCEL로 보내면 MCP/Spring 쪽에서 취소로 해석해 GO_HOME을 내려줄 수 있어서,
     * 화면이 이전 단계가 아니라 메인으로 돌아가는 문제가 생긴다.
     */
    const activeSessionId = sessionId || sessionIdRef.current || FALLBACK_STEP_SESSION_ID;

    await safeSendFrontEvent('USER_TOUCH', {
      sessionId: activeSessionId,
      action: 'PREV',
      from: screen,
      to: prev,
    });

    // 이전 버튼도 실제 단계 이동이므로 TC-FE-08/09 확인을 위해 STEP_CHANGE를 반드시 보낸다.
    await safeSendStepChange(prev, activeSessionId);
    screenRef.current = prev;
    setScreen(prev);
  };

  const handleNext = async () => {
    unlockSpeechSynthesis();
    const nextMap = {
      [STEP_SERVICE]: STEP_VERIFY,
      [STEP_VERIFY]: STEP_ISSUE_CONTENT,
      [STEP_ISSUE_CONTENT]: STEP_COPY_COUNT,
      [STEP_COPY_COUNT]: STEP_CONFIRM,
      [STEP_TRANSFER_IDENTITY]: STEP_TRANSFER_REASON,
      [STEP_TRANSFER_REASON]: STEP_TRANSFER_PREVIOUS_SEARCH,
      [STEP_TRANSFER_PREVIOUS_SEARCH]: STEP_TRANSFER_CURRENT_ADDRESS,
      [STEP_TRANSFER_CURRENT_ADDRESS]: STEP_TRANSFER_HOUSEHOLD,
      [STEP_TRANSFER_HOUSEHOLD]: STEP_TRANSFER_SERVICE,
      [STEP_TRANSFER_SERVICE]: STEP_TRANSFER_CONFIRM,
    };

    const next = nextMap[screen];
    if (!next) return;

    const activeSessionId = sessionId || sessionIdRef.current || FALLBACK_STEP_SESSION_ID;

    await safeSendFrontEvent('USER_TOUCH', {
      sessionId: activeSessionId,
      action: 'NEXT',
      from: screen,
      to: next,
    });

    await safeSendStepChange(next, activeSessionId);
    screenRef.current = next;
    setScreen(next);
  };

  const handleIssueTypeChange = async (issueType) => {
    setForm((prev) => ({
      ...prev,
      issueType,
      selectedHistoryOptions: issueType === 'all' ? [] : prev.selectedHistoryOptions,
    }));

    safeSendFrontEvent('USER_TOUCH', {
      sessionId,
      action: 'CHANGE_ISSUE_TYPE',
      issueType,
    });
  };

  const toggleHistoryOption = async (option) => {
    setForm((prev) => ({
      ...prev,
      selectedHistoryOptions: prev.selectedHistoryOptions.includes(option)
        ? prev.selectedHistoryOptions.filter((item) => item !== option)
        : [...prev.selectedHistoryOptions, option],
    }));

    safeSendFrontEvent('USER_TOUCH', {
      sessionId,
      action: 'TOGGLE_HISTORY_OPTION',
      option,
    });
  };

  const updateTransferField = async (field, value) => {
    setForm((prev) => ({
      ...prev,
      transfer: {
        ...prev.transfer,
        [field]: value,
      },
    }));

    safeSendFrontEvent('USER_TOUCH', {
      sessionId,
      action: 'CHANGE_TRANSFER_FIELD',
      field,
      value,
    });
  };

  const toggleMovingMember = async (memberId) => {
    setForm((prev) => {
      const selected = prev.transfer.movingMembers.includes(memberId);
      return {
        ...prev,
        transfer: {
          ...prev.transfer,
          movingMembers: selected
            ? prev.transfer.movingMembers.filter((item) => item !== memberId)
            : [...prev.transfer.movingMembers, memberId],
        },
      };
    });

    safeSendFrontEvent('USER_TOUCH', {
      sessionId,
      action: 'TOGGLE_TRANSFER_MEMBER',
      memberId,
    });
  };

  const toggleTransferExtraService = async (serviceId) => {
    setForm((prev) => {
      const selected = prev.transfer.extraServices.includes(serviceId);
      return {
        ...prev,
        transfer: {
          ...prev.transfer,
          extraServices: selected
            ? prev.transfer.extraServices.filter((item) => item !== serviceId)
            : [...prev.transfer.extraServices, serviceId],
        },
      };
    });

    safeSendFrontEvent('USER_TOUCH', {
      sessionId,
      action: 'TOGGLE_TRANSFER_EXTRA_SERVICE',
      serviceId,
    });
  };

  const handleSubmit = async () => {
    const payload = {
      sessionId,
      serviceId: form.selectedServiceId,
      serviceName: confirmSummary.serviceName,
      residentRegistrationNumber: `${form.residentFront}-${form.residentBack}`,
      issueType: form.issueType,
      selectedOptions: form.selectedHistoryOptions,
      copyCount: Number(form.copyCount),
      feePerCopy: FEE_PER_COPY,
      totalFee,
    };

    const activeSessionId = sessionId || sessionIdRef.current || FALLBACK_STEP_SESSION_ID;

    await safeSendStepChange(STEP_CONFIRM, activeSessionId);
    await safeSendFrontEvent('SERVICE_COMPLETE', {
      sessionId: activeSessionId,
      serviceId: form.selectedServiceId,
      serviceName: confirmSummary.serviceName,
    });
    setStatusMessage('서비스 완료 이벤트를 전송했습니다. 잠시 후 처음 화면으로 이동합니다.');
  };

  const handleTransferSubmit = async () => {
    const payload = {
      sessionId,
      serviceId: form.selectedServiceId || 'p1',
      serviceName: form.selectedServiceLabel || '전입신고',
      applicantName: form.transfer.name,
      residentRegistrationNumber: `${form.transfer.residentFront}-${form.transfer.residentBack}`,
      phoneNumber: `${form.transfer.phone1}-${form.transfer.phone2}-${form.transfer.phone3}`,
      reason: form.transfer.reason,
      previousAddress: {
        sido: form.transfer.prevSido,
        sigungu: form.transfer.prevSigungu,
        address: form.transfer.prevAddress,
        adminCenter: form.transfer.prevAdminCenter,
      },
      movingMembers: form.transfer.movingMembers,
      currentAddress: {
        baseAddress: form.transfer.currentBaseAddress,
        buildingType: form.transfer.buildingType,
        buildingMainNo: form.transfer.buildingMainNo,
        buildingSubNo: form.transfer.buildingSubNo,
        detailAddress: form.transfer.detailAddress,
      },
      householdType: form.transfer.householdType,
      extraServices: form.transfer.extraServices,
    };

    const activeSessionId = sessionId || sessionIdRef.current || FALLBACK_STEP_SESSION_ID;

    await safeSendStepChange(STEP_TRANSFER_CONFIRM, activeSessionId);
    await safeSendFrontEvent('SERVICE_COMPLETE', {
      sessionId: activeSessionId,
      serviceId: form.selectedServiceId || 'p1',
      serviceName: form.selectedServiceLabel || '전입신고',
    });
    setStatusMessage('서비스 완료 이벤트를 전송했습니다. 잠시 후 처음 화면으로 이동합니다.');
  };

  const handleVoiceMicClick = () => {
    if (!accessibility.voiceMode) return;

    if (voiceUi.listening) {
      stopVoiceRecognition();
      setVoiceUi((prev) => ({
        ...prev,
        listening: false,
        guideText: WAITING_VOICE_GUIDE_TEXT,
      }));
      return;
    }

    setVoicePanelVisible(true);
    setVoiceUi((prev) => ({
      ...prev,
      transcript: '',
      error: '',
      guideText: '듣고 있습니다. 원하는 서비스를 말씀해 주세요.',
    }));
    startVoiceRecognition();
  };

  const renderScreen = () => {
    switch (screen) {
      case STEP_MAIN:
        return (
          <MainScreen
            categories={categories}
            onSelectService={handleMainServiceClick}
          />
        );

      case STEP_SERVICE:
        return (
          <ServiceSelect
            selectedServiceId={form.selectedServiceId}
            onSelect={handleSelectService}
            onHome={resetToHome}
            onPrev={handlePrev}
            onNext={handleNext}
          />
        );

      case STEP_VERIFY:
        return (
          <IdentityVerify
            residentFront={form.residentFront}
            residentBack={form.residentBack}
            onKeypadPress={handleResidentKeypad}
            onHome={resetToHome}
            onPrev={handlePrev}
            onNext={handleNext}
          />
        );

      case STEP_ISSUE_CONTENT:
        return (
          <IssueContentPage
            issueType={form.issueType}
            options={DEFAULT_HISTORY_OPTIONS}
            selectedOptions={form.selectedHistoryOptions}
            onIssueTypeChange={handleIssueTypeChange}
            onToggleOption={toggleHistoryOption}
            onHome={resetToHome}
            onPrev={handlePrev}
            onNext={handleNext}
          />
        );

      case STEP_COPY_COUNT:
        return (
          <CopyCountPage
            copyCount={form.copyCount}
            onKeypadPress={handleCopyCountKeypad}
            onHome={resetToHome}
            onPrev={handlePrev}
            onNext={handleNext}
          />
        );

      case STEP_CONFIRM:
        return (
          <ConfirmFee
            summary={confirmSummary}
            fee={FEE_PER_COPY}
            totalFee={totalFee}
            onHome={resetToHome}
            onPrev={handlePrev}
            onSubmit={handleSubmit}
          />
        );

      case STEP_TRANSFER_IDENTITY:
        return (
          <TransferIdentityInfo
            data={form.transfer}
            onChange={updateTransferField}
            onResidentKeypad={handleTransferResidentKeypad}
            onHome={resetToHome}
            onPrev={handlePrev}
            onNext={handleNext}
          />
        );

      case STEP_TRANSFER_REASON:
        return (
          <TransferReason
            data={form.transfer}
            onSelectReason={(reason) => updateTransferField('reason', reason)}
            onHome={resetToHome}
            onPrev={handlePrev}
            onNext={handleNext}
          />
        );

      case STEP_TRANSFER_PREVIOUS_SEARCH:
        return (
          <TransferPreviousInfo
            data={form.transfer}
            onChange={updateTransferField}
            onToggleMember={toggleMovingMember}
            onHome={resetToHome}
            onPrev={handlePrev}
            onNext={handleNext}
          />
        );

      case STEP_TRANSFER_CURRENT_ADDRESS:
        return (
          <TransferCurrentAddressInfo
            data={form.transfer}
            onChange={updateTransferField}
            onHome={resetToHome}
            onPrev={handlePrev}
            onNext={handleNext}
          />
        );

      case STEP_TRANSFER_HOUSEHOLD:
        return (
          <TransferHousehold
            data={form.transfer}
            onChange={updateTransferField}
            onHome={resetToHome}
            onPrev={handlePrev}
            onNext={handleNext}
          />
        );

      case STEP_TRANSFER_SERVICE:
        return (
          <TransferExtraService
            data={form.transfer}
            onToggleExtraService={toggleTransferExtraService}
            onHome={resetToHome}
            onPrev={handlePrev}
            onNext={handleNext}
          />
        );

      case STEP_TRANSFER_CONFIRM:
        return (
          <TransferConfirm
            data={form.transfer}
            onHome={resetToHome}
            onPrev={handlePrev}
            onSubmit={handleTransferSubmit}
          />
        );

      default:
        return null;
    }
  };

  return (
    <div className="app-shell">
      <ScreenFrame accessibility={accessibility}>
        {screen === STEP_MAIN ? (
          <>
            {renderScreen()}
            <div className="main-mode-bar-wrap">
              <ModeBar accessibility={accessibility} onAction={handleAccessibilityAction} />
            </div>
          </>
        ) : (
          <div className="flow-screen-stack">
            <div className="flow-mode-bar-wrap">
              <ModeBar accessibility={accessibility} onAction={handleAccessibilityAction} />
            </div>
            {renderScreen()}
          </div>
        )}
        <VoicePanel
          active={accessibility.voiceMode && voicePanelVisible}
          listening={voiceUi.listening}
          supported={voiceUi.supported}
          transcript={voiceUi.transcript}
          guideText={voiceUi.guideText}
          error={voiceUi.error}
          onMicClick={handleVoiceMicClick}
          onClose={turnOffVoiceMode}
        />
        {statusMessage ? <div className="status-message">{statusMessage}</div> : null}
        {submittedApplicationNo ? (
          <div className="status-message">신청번호: {submittedApplicationNo}</div>
        ) : null}
      </ScreenFrame>
    </div>
  );
}
