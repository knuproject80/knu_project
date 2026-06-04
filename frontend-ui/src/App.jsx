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
const STEP_TRANSFER_PREV_ADDR = 'transfer_prev_addr';
const STEP_TRANSFER_NEW_ADDR = 'transfer_new_addr';
const STEP_TRANSFER_HOUSEHOLD = 'transfer_household';
const STEP_TRANSFER_EXTRA = 'transfer_extra';
const STEP_TRANSFER_CONFIRM = 'transfer_confirm';

// 🚀 [수정 포인트 1] 누락되었던 STEP_VERIFY 등을 추가하고 오타 수정
const STEP_KEYS = {
  [STEP_SERVICE]: 'CERTIFICATE_SELECT_PURPOSE',
  [STEP_VERIFY]: 'CERTIFICATE_SELECT_RRN',
  [STEP_ISSUE_CONTENT]: 'CERTIFICATE_SELECT_SCOPE',
  [STEP_COPY_COUNT]: 'CERTIFICATE_SELECT_COUNT',
  [STEP_CONFIRM]: 'CERTIFICATE_CONFIRM',
  [STEP_TRANSFER_IDENTITY]: 'MOVEIN_INPUT_BASIC_INFO',
  [STEP_TRANSFER_REASON]: 'MOVEIN_SELECT_REASON',
  [STEP_TRANSFER_PREV_ADDR]: 'MOVEIN_INPUT_PREV_ADDRESS',
  [STEP_TRANSFER_NEW_ADDR]: 'MOVEIN_INPUT_NEW_ADDRESS',
  [STEP_TRANSFER_HOUSEHOLD]: 'MOVEIN_SELECT_HOUSEHOLD',
  [STEP_TRANSFER_EXTRA]: 'MOVEIN_SELECT_EXTRA_SERVICE',
  [STEP_TRANSFER_CONFIRM]: 'MOVEIN_CONFIRM',
};

function getStepKey(screen) {
  return STEP_KEYS[screen] || 'UNKNOWN_STEP';
}

function speakText(text, onEnd) {
  if (!text) {
    onEnd?.();
    return;
  }
  if (!window.speechSynthesis) {
    onEnd?.();
    return;
  }
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = 'ko-KR';
  utterance.rate = 1.0;
  if (onEnd) {
    utterance.onend = onEnd;
    utterance.onerror = onEnd;
  }
  window.speechSynthesis.speak(utterance);
}

export default function App() {
  const [screen, setScreen] = useState(STEP_MAIN);
  const [sessionId, setSessionId] = useState(null);
  const [statusMessage, setStatusMessage] = useState('');
  const [submittedApplicationNo, setSubmittedApplicationNo] = useState(null);

  const [accessibility, setAccessibility] = useState({
    largeFont: false,
    highContrast: false,
    simpleMode: false,
    lowScreenMode: false,
    voiceMode: false,
    fontSize: 16,
  });

  const [voiceUi, setVoiceUi] = useState({
    listening: false,
    supported: false,
    transcript: '',
    guideText: '',
    error: '',
  });

  const [form, setForm] = useState({
    serviceId: null,
    serviceName: '',
    residentNumber: '',
    residentFront: '',
    residentBack: '',
    certificate: {
      issueType: null,
      selectedOptions: [],
      copyCount: '',
    },
    transfer: {
      name: '김성애',
      phone1: '010',
      phone2: '1234',
      phone3: '5678',
      reason: '',
      prevAddress: '대구광역시 북구 대학로 80',
      prevAdminCenter: '대현동 주민센터',
      movingMembers: ['self'],
      newAddress: '',
      buildingType: 'ground',
      householdType: '',
      extraServices: [],
    },
  });

  const voicePanelVisible =
    accessibility.voiceMode && screen !== STEP_MAIN && !submittedApplicationNo;

  const currentStep = useMemo(() => {
    if (form.serviceId === 102) {
      if (screen === STEP_SERVICE) return 1;
      if (screen === STEP_VERIFY) return 2;
      if (screen === STEP_ISSUE_CONTENT || screen === STEP_COPY_COUNT) return 3;
      if (screen === STEP_CONFIRM) return 4;
    }
    if (form.serviceId === 101) {
      if (screen === STEP_SERVICE) return 1;
      if (screen === STEP_TRANSFER_IDENTITY) return 1;
      if (screen === STEP_TRANSFER_REASON) return 2;
      if (screen === STEP_TRANSFER_PREV_ADDR) return 3;
      if (screen === STEP_TRANSFER_NEW_ADDR) return 4;
      if (screen === STEP_TRANSFER_HOUSEHOLD) return 5;
      if (screen === STEP_TRANSFER_EXTRA) return 6;
      if (screen === STEP_TRANSFER_CONFIRM) return 7;
    }
    return 1;
  }, [screen, form.serviceId]);

  const recognitionRef = useRef(null);
  const recognitionState = useRef('stopped');

  const updateVoiceUi = useCallback((updates) => {
    setVoiceUi((prev) => ({ ...prev, ...updates }));
  }, []);

  const turnOffVoiceMode = useCallback(() => {
    setAccessibility((prev) => ({ ...prev, voiceMode: false }));
    updateVoiceUi({ listening: false, transcript: '', guideText: '' });
    if (recognitionRef.current) {
      recognitionRef.current.abort();
    }
  }, [updateVoiceUi]);

  const handleUiCommand = useCallback(
    (payload) => {
      const action = payload.action;
      const data = payload.data || {};

      if (action === 'ADAPT_UI') {
        const settings = data.settings || {};
        setAccessibility((prev) => ({
          ...prev,
          largeFont: Boolean(settings.largeFont),
          highContrast: Boolean(settings.highContrast),
          simpleMode: Boolean(settings.simpleMode),
          lowScreenMode: Boolean(settings.lowScreenMode),
          fontSize: settings.fontSize ? parseInt(settings.fontSize, 10) : 16,
        }));
        if (data.userType === 'ELDERLY' || data.userType === 'WHEELCHAIR') {
          setAccessibility((prev) => ({ ...prev, voiceMode: true }));
        }
        sendUiAck('ADAPT_UI', { commandId: payload.commandId, sessionId: data.sessionId });
      
      } else if (action === 'VOICE_GUIDE') {
        updateVoiceUi({ guideText: data.guideText });
        
        // 🚀 [수정 포인트 2] autoAdvance true 일 때 폼 데이터를 채우고 다음 페이지로 넘기는 함수 추가
        const advanceStep = () => {
          if (data.context === 'CERTIFICATE_SELECT_SCOPE') {
            setForm((prev) => ({
              ...prev,
              certificate: { ...prev.certificate, issueType: 'select', selectedOptions: [data.prefilledValue] }
            }));
            setScreen(STEP_COPY_COUNT);
          } else if (data.context === 'CERTIFICATE_SELECT_COUNT') {
            setForm((prev) => ({
              ...prev,
              certificate: { ...prev.certificate, copyCount: String(data.prefilledValue) }
            }));
            setScreen(STEP_CONFIRM);
          }
        };

        if (data.autoAdvance) {
          // 어르신 모드: 음성을 읽은 후 페이지 스킵
          if (data.userType === 'ELDERLY' && data.autoAdvanceGuide) {
            speakText(data.autoAdvanceGuide, () => {
              advanceStep();
            });
          } else {
            // 그 외 모드: 즉시 스킵
            advanceStep();
          }
        } else if (data.guideText) {
          // 일반 음성 안내
          speakText(data.guideText, () => {
             // TTS 완료 후 로직
          });
        }
      } else if (action === 'MOVE_PAGE') {
        const { serviceId, serviceName } = data;
        setForm((prev) => ({ ...prev, serviceId, serviceName }));
        if (serviceId === 102) setScreen(STEP_VERIFY);
        else if (serviceId === 101) setScreen(STEP_TRANSFER_IDENTITY);
        sendUiAck('MOVE_PAGE', { commandId: payload.commandId, sessionId: data.sessionId });
      } else if (action === 'SESSION_EXPIRED') {
        setStatusMessage(data.message || '시간 초과로 홈으로 이동합니다.');
        sendUiAck('SESSION_EXPIRED', { commandId: payload.commandId, sessionId: data.sessionId });
        setTimeout(() => {
          window.location.reload();
        }, 3000);
      } else if (action === 'GO_HOME') {
        setStatusMessage(data.message || '홈으로 이동합니다.');
        sendUiAck('GO_HOME', { commandId: payload.commandId, sessionId: data.sessionId });
        setTimeout(() => {
          window.location.reload();
        }, 3000);
      }
    },
    [updateVoiceUi]
  );

  useEffect(() => {
    connectStomp()
      .then(() => {
        subscribeUiCommands({ onCommand: handleUiCommand });
        subscribeFrontAck();
      })
      .catch((err) => console.error('STOMP init error', err));

    return () => {
      disconnectStomp();
    };
  }, [handleUiCommand]);

  useEffect(() => {
    if ('webkitSpeechRecognition' in window) {
      updateVoiceUi({ supported: true });
      const SpeechRecognition = window.webkitSpeechRecognition;
      const reco = new SpeechRecognition();
      reco.continuous = false;
      reco.interimResults = false;
      reco.lang = 'ko-KR';

      reco.onstart = () => {
        recognitionState.current = 'started';
        updateVoiceUi({ listening: true, error: '', transcript: '' });
      };

      reco.onresult = (event) => {
        const text = event.results[0][0].transcript;
        updateVoiceUi({ transcript: text });

        sendFrontEvent('VOICE_INPUT', {
          text,
          sessionId,
          locale: 'ko-KR',
        });
      };

      reco.onerror = (event) => {
        if (event.error === 'no-speech' || event.error === 'aborted') {
          return;
        }
        updateVoiceUi({ error: `음성 인식 오류: ${event.error}` });
      };

      reco.onend = () => {
        recognitionState.current = 'stopped';
        updateVoiceUi({ listening: false });
      };

      recognitionRef.current = reco;
    }
  }, [updateVoiceUi, sessionId]);

  const toggleListening = useCallback(() => {
    if (!recognitionRef.current) return;
    if (recognitionState.current === 'started') {
      recognitionRef.current.stop();
    } else {
      try {
        recognitionRef.current.start();
      } catch (e) {
        console.warn('Recognition start failed', e);
      }
    }
  }, []);

  const handleVoiceMicClick = useCallback(() => {
    toggleListening();
  }, [toggleListening]);

  useEffect(() => {
    if (screen !== STEP_MAIN && screen !== STEP_SERVICE) {
      if (sessionId) {
        sendStepChange({ sessionId, step: getStepKey(screen) });
      }
    }
  }, [screen, sessionId]);

  const handleAccessibilityAction = (key) => {
    setAccessibility((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const handleSelectService = (item) => {
    setForm((prev) => ({ ...prev, serviceId: item.id, serviceName: item.name }));
    sendFrontEvent('TOUCH_SERVICE', { serviceId: item.id });
  };

  const handleKeypadPress = (key) => {
    if (key === '완료') return;

    if (screen === STEP_VERIFY || screen === STEP_TRANSFER_IDENTITY) {
      setForm((prev) => {
        let f = prev.residentFront;
        let b = prev.residentBack;
        if (key === 'X') {
          if (b.length > 0) b = b.slice(0, -1);
          else if (f.length > 0) f = f.slice(0, -1);
        } else {
          if (f.length < 6) f += key;
          else if (b.length < 7) b += key;
        }
        return { ...prev, residentFront: f, residentBack: b, residentNumber: `${f}-${b}` };
      });
    }

    if (screen === STEP_COPY_COUNT) {
      setForm((prev) => {
        let count = prev.certificate.copyCount;
        if (key === 'X') {
          count = count.slice(0, -1);
        } else {
          if (count.length < 2) count += key;
        }
        return { ...prev, certificate: { ...prev.certificate, copyCount: count } };
      });
    }
  };

  const handlePrev = () => {
    if (screen === STEP_VERIFY) setScreen(STEP_SERVICE);
    else if (screen === STEP_ISSUE_CONTENT) setScreen(STEP_VERIFY);
    else if (screen === STEP_COPY_COUNT) setScreen(STEP_ISSUE_CONTENT);
    else if (screen === STEP_CONFIRM) setScreen(STEP_COPY_COUNT);

    else if (screen === STEP_TRANSFER_REASON) setScreen(STEP_TRANSFER_IDENTITY);
    else if (screen === STEP_TRANSFER_PREV_ADDR) setScreen(STEP_TRANSFER_REASON);
    else if (screen === STEP_TRANSFER_NEW_ADDR) setScreen(STEP_TRANSFER_PREV_ADDR);
    else if (screen === STEP_TRANSFER_HOUSEHOLD) setScreen(STEP_TRANSFER_NEW_ADDR);
    else if (screen === STEP_TRANSFER_EXTRA) setScreen(STEP_TRANSFER_HOUSEHOLD);
    else if (screen === STEP_TRANSFER_CONFIRM) setScreen(STEP_TRANSFER_EXTRA);
  };

  const handleNext = () => {
    if (screen === STEP_VERIFY) setScreen(STEP_ISSUE_CONTENT);
    else if (screen === STEP_ISSUE_CONTENT) setScreen(STEP_COPY_COUNT);
    else if (screen === STEP_COPY_COUNT) setScreen(STEP_CONFIRM);

    else if (screen === STEP_TRANSFER_IDENTITY) setScreen(STEP_TRANSFER_REASON);
    else if (screen === STEP_TRANSFER_REASON) setScreen(STEP_TRANSFER_PREV_ADDR);
    else if (screen === STEP_TRANSFER_PREV_ADDR) setScreen(STEP_TRANSFER_NEW_ADDR);
    else if (screen === STEP_TRANSFER_NEW_ADDR) setScreen(STEP_TRANSFER_HOUSEHOLD);
    else if (screen === STEP_TRANSFER_HOUSEHOLD) setScreen(STEP_TRANSFER_EXTRA);
    else if (screen === STEP_TRANSFER_EXTRA) setScreen(STEP_TRANSFER_CONFIRM);
  };

  const resetToHome = () => {
    sendFrontEvent('USER_CANCEL', { sessionId });
  };

  const handleCertificateSubmit = () => {
    sendFrontEvent('SERVICE_COMPLETE', { sessionId });
  };

  const handleTransferSubmit = () => {
    sendFrontEvent('SERVICE_COMPLETE', { sessionId });
  };


  const renderScreen = () => {
    switch (screen) {
      case STEP_MAIN:
        return <MainScreen categories={LOCAL_SERVICE_CATEGORIES} onSelectService={handleSelectService} />;
      case STEP_SERVICE:
        return (
          <ServiceSelect
            selectedServiceId={form.serviceId}
            onSelect={(item) => setForm({ ...form, serviceId: item.id })}
            onHome={resetToHome}
            onPrev={() => setScreen(STEP_MAIN)}
            onNext={() => setScreen(form.serviceId === 102 ? STEP_VERIFY : STEP_TRANSFER_IDENTITY)}
          />
        );
      case STEP_VERIFY:
        return (
          <IdentityVerify
            residentFront={form.residentFront}
            residentBack={form.residentBack}
            onKeypadPress={handleKeypadPress}
            onHome={resetToHome}
            onPrev={handlePrev}
            onNext={handleNext}
          />
        );
      case STEP_ISSUE_CONTENT:
        return (
          <IssueContentPage
            issueType={form.certificate.issueType}
            options={DEFAULT_HISTORY_OPTIONS}
            selectedOptions={form.certificate.selectedOptions}
            onIssueTypeChange={(val) => setForm({ ...form, certificate: { ...form.certificate, issueType: val, selectedOptions: [] } })}
            onToggleOption={(opt) => {
              setForm((prev) => {
                const sel = prev.certificate.selectedOptions;
                const nextSel = sel.includes(opt) ? sel.filter((o) => o !== opt) : [...sel, opt];
                return { ...prev, certificate: { ...prev.certificate, selectedOptions: nextSel } };
              });
            }}
            onHome={resetToHome}
            onPrev={handlePrev}
            onNext={handleNext}
          />
        );
      case STEP_COPY_COUNT:
        return (
          <CopyCountPage
            copyCount={form.certificate.copyCount}
            onKeypadPress={handleKeypadPress}
            onHome={resetToHome}
            onPrev={handlePrev}
            onNext={handleNext}
          />
        );
      case STEP_CONFIRM:
        return (
          <ConfirmFee
            summary={{
              serviceName: form.serviceName,
              residentNumber: form.residentNumber,
              issueTypeLabel: form.certificate.issueType === 'select' ? '선택발급' : '전체발급',
              selectedOptions: form.certificate.selectedOptions,
              copyCount: form.certificate.copyCount,
            }}
            fee={500}
            totalFee={500 * (Number(form.certificate.copyCount) || 1)}
            onHome={resetToHome}
            onPrev={handlePrev}
            onSubmit={handleCertificateSubmit}
          />
        );

      // Transfer Screens...
      case STEP_TRANSFER_IDENTITY:
        return <TransferIdentityInfo residentFront={form.residentFront} residentBack={form.residentBack} onKeypadPress={handleKeypadPress} onHome={resetToHome} onPrev={handlePrev} onNext={handleNext} />;
      case STEP_TRANSFER_REASON:
        return <TransferReason selected={form.transfer.reason} onSelect={(val) => setForm((prev) => ({ ...prev, transfer: { ...prev.transfer, reason: val } }))} onHome={resetToHome} onPrev={handlePrev} onNext={handleNext} />;
      case STEP_TRANSFER_PREV_ADDR:
        return <TransferPreviousInfo data={form.transfer} onHome={resetToHome} onPrev={handlePrev} onNext={handleNext} />;
      case STEP_TRANSFER_NEW_ADDR:
        return <TransferCurrentAddressInfo data={form.transfer} onChange={(k, v) => setForm((prev) => ({ ...prev, transfer: { ...prev.transfer, [k]: v } }))} onHome={resetToHome} onPrev={handlePrev} onNext={handleNext} />;
      case STEP_TRANSFER_HOUSEHOLD:
        return <TransferHousehold selected={form.transfer.householdType} onSelect={(val) => setForm((prev) => ({ ...prev, transfer: { ...prev.transfer, householdType: val } }))} onHome={resetToHome} onPrev={handlePrev} onNext={handleNext} />;
      case STEP_TRANSFER_EXTRA:
        return <TransferExtraService selected={form.transfer.extraServices} onToggle={(val) => setForm((prev) => {
          const sel = prev.transfer.extraServices;
          const nextSel = sel.includes(val) ? sel.filter(s => s !== val) : [...sel, val];
          return { ...prev, transfer: { ...prev.transfer, extraServices: nextSel } };
        })} onHome={resetToHome} onPrev={handlePrev} onNext={handleNext} />;
      case STEP_TRANSFER_CONFIRM:
        return <TransferConfirm residentNumber={form.residentNumber} data={form.transfer} onHome={resetToHome} onPrev={handlePrev} onSubmit={handleTransferSubmit} />;

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