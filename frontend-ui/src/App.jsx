import { useEffect, useMemo, useRef, useState } from 'react';
import MainScreen from './components/MainScreen';
import ScreenFrame from './components/ScreenFrame';
import ServiceSelect from './components/ServiceSelect';
import IdentityVerify from './components/IdentityVerify';
import ConfirmFee from './components/ConfirmFee';
import { CopyCountPage, IssueContentPage } from './components/IssueContent';
import './styles/App.css';
import { DEFAULT_HISTORY_OPTIONS, LOCAL_SERVICE_CATEGORIES, USER_TYPES } from './data/options';
import {
  connectStomp,
  subscribeFrontAck,
  subscribeUiCommands,
  sendFrontEvent,
  sendUiAck,
  disconnectStomp,
} from './api/api';

const STEP_MAIN = 'main';
const STEP_SERVICE = 'service';
const STEP_VERIFY = 'verify';
const STEP_ISSUE_CONTENT = 'issue_content';
const STEP_COPY_COUNT = 'copy_count';
const STEP_CONFIRM = 'confirm';

const FEE_PER_COPY = 400;

const initialForm = {
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
};

export default function App() {
  const [screen, setScreen] = useState(STEP_MAIN);
  const [categories] = useState(LOCAL_SERVICE_CATEGORIES);
  const [sessionId, setSessionId] = useState('');
  const [accessibility, setAccessibility] = useState(USER_TYPES.NORMAL);
  const [statusMessage, setStatusMessage] = useState('');
  const [submittedApplicationNo, setSubmittedApplicationNo] = useState('');
  const [form, setForm] = useState(initialForm);

  const submitResetTimerRef = useRef(null);

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
        await sendFrontEvent('FRONT_READY', { ui: 'kiosk' });

        // 세션은 서버가 내려주는 값을 받는 구조로 가정
        await subscribeUiCommands({
          sessionId: '',
          onCommand: async (message) => {
            if (!mounted || !message) return;

            const action = message.action;
            const data = message.data || {};

            if (action === 'SESSION_ASSIGNED') {
              if (data.sessionId) {
                setSessionId(data.sessionId);
              }
              return;
            }

            if (action === 'ADAPT_UI') {
              if (data.accessibility) {
                setAccessibility((prev) => ({
                  ...prev,
                  ...data.accessibility,
                  fontSize: Number.parseInt(data.accessibility.fontSize, 10) || prev.fontSize,
                }));
              }
              await sendUiAck('ADAPT_UI', {
                sessionId: data.sessionId || sessionId,
              });
              return;
            }

            if (action === 'MOVE_PAGE') {
              const targetPage = data.page;
              const allowedPages = [
                STEP_MAIN,
                STEP_SERVICE,
                STEP_VERIFY,
                STEP_ISSUE_CONTENT,
                STEP_COPY_COUNT,
                STEP_CONFIRM,
              ];

              if (allowedPages.includes(targetPage)) {
                setScreen(targetPage);
              }

              await sendUiAck('MOVE_PAGE', {
                sessionId: data.sessionId || sessionId,
                page: targetPage,
              });
              return;
            }

            if (action === 'GO_HOME') {
              clearSubmitResetTimer();
              setForm(initialForm);
              setSubmittedApplicationNo('');
              setStatusMessage('');
              setScreen(STEP_MAIN);

              await sendUiAck('GO_HOME', {
                sessionId: data.sessionId || sessionId,
              });
              return;
            }

            if (action === 'SESSION_EXPIRED') {
              clearSubmitResetTimer();
              setForm(initialForm);
              setSubmittedApplicationNo('');
              setStatusMessage('세션이 만료되었습니다. 처음 화면으로 이동합니다.');
              setScreen(STEP_MAIN);
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

              clearSubmitResetTimer();
              submitResetTimerRef.current = setTimeout(() => {
                setForm(initialForm);
                setSubmittedApplicationNo('');
                setStatusMessage('');
                setScreen(STEP_MAIN);
              }, 2500);
            }
          },
        });
      } catch (error) {
        console.error(error);
        setStatusMessage('서버 연결에 실패했습니다.');
      }
    }

    bootstrap();

    return () => {
      mounted = false;
      clearSubmitResetTimer();
      disconnectStomp();
    };
  }, []);

  const clearSubmitResetTimer = () => {
    if (submitResetTimerRef.current) {
      clearTimeout(submitResetTimerRef.current);
      submitResetTimerRef.current = null;
    }
  };

  const confirmSummary = useMemo(() => {
    const serviceName = form.selectedServiceLabel || form.selectedMenuName || '주민등록등본 발급';
    const issueTypeLabel = form.issueType === 'all' ? '전체발급' : '선택발급';

    return {
      serviceName,
      issueTypeLabel,
      selectedOptions: form.issueType === 'select' ? form.selectedHistoryOptions : [],
      copyCount: form.copyCount || '1',
    };
  }, [form]);

  const totalFee = (Number(form.copyCount) || 0) * FEE_PER_COPY;

  const resetToHome = async () => {
    clearSubmitResetTimer();
    await sendFrontEvent('USER_CANCEL', { sessionId });
    setForm(initialForm);
    setSubmittedApplicationNo('');
    setStatusMessage('');
    setScreen(STEP_MAIN);
  };

  const handleAccessibilityAction = async (actionKey) => {
    // 키 이름 통일: MainScreen은 voiceMode를 보고 있는데
    // 기존 App 쪽은 voiceGuide를 쓰고 있어서 여기 맞춰줌
    if (actionKey === 'voiceMode') {
      setAccessibility((prev) => ({
        ...prev,
        voiceMode: !prev.voiceMode,
      }));

      await sendFrontEvent('TOGGLE_ACCESSIBILITY', {
        sessionId,
        actionKey,
        enabled: !accessibility.voiceMode,
      });
      return;
    }

    const nextAccessibility = { ...accessibility };

    if (actionKey === 'highContrast') {
      nextAccessibility.highContrast = !nextAccessibility.highContrast;
    } else if (actionKey === 'largeFont') {
      nextAccessibility.largeFont = !nextAccessibility.largeFont;
      nextAccessibility.fontSize = nextAccessibility.largeFont ? 24 : 16;
    } else if (actionKey === 'lowScreenMode') {
      nextAccessibility.lowScreenMode = !nextAccessibility.lowScreenMode;
    }

    setAccessibility(nextAccessibility);

    await sendFrontEvent('TOGGLE_ACCESSIBILITY', {
      sessionId,
      actionKey,
      accessibility: nextAccessibility,
    });
  };

  const handleMainServiceClick = async (item) => {
    await sendFrontEvent('USER_TOUCH', {
      sessionId,
      action: 'SELECT_MAIN_MENU',
      menuId: item.id,
    });

    if (item.type === 'resident') {
      setForm((prev) => ({
        ...prev,
        categoryId: 'certificate',
        categoryTitle: '증명서발급',
        selectedMenuId: item.id,
        selectedMenuName: item.name,
      }));
      setScreen(STEP_SERVICE);
      return;
    }

    setStatusMessage('현재 예시는 주민등록등본/초본 흐름만 구현되어 있습니다.');
  };

  const handleSelectService = async (service) => {
    setForm((prev) => ({
      ...prev,
      selectedServiceId: service.id,
      selectedServiceLabel: service.label,
    }));

    await sendFrontEvent('USER_TOUCH', {
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

    await sendFrontEvent('USER_TOUCH', {
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

    await sendFrontEvent('USER_TOUCH', {
      sessionId,
      action: 'INPUT_COPY_COUNT',
      key,
    });
  };

  const handlePrev = async () => {
    const prevMap = {
      [STEP_SERVICE]: STEP_MAIN,
      [STEP_VERIFY]: STEP_SERVICE,
      [STEP_ISSUE_CONTENT]: STEP_VERIFY,
      [STEP_COPY_COUNT]: STEP_ISSUE_CONTENT,
      [STEP_CONFIRM]: STEP_COPY_COUNT,
    };

    const prev = prevMap[screen];
    if (!prev) return;

    await sendFrontEvent('USER_CANCEL', {
      sessionId,
      from: screen,
      to: prev,
    });

    setScreen(prev);
  };

  const handleNext = async () => {
    const nextMap = {
      [STEP_SERVICE]: STEP_VERIFY,
      [STEP_VERIFY]: STEP_ISSUE_CONTENT,
      [STEP_ISSUE_CONTENT]: STEP_COPY_COUNT,
      [STEP_COPY_COUNT]: STEP_CONFIRM,
    };

    const next = nextMap[screen];
    if (!next) return;

    await sendFrontEvent('USER_TOUCH', {
      sessionId,
      action: 'NEXT',
      from: screen,
      to: next,
    });

    setScreen(next);
  };

  const handleIssueTypeChange = async (issueType) => {
    setForm((prev) => ({
      ...prev,
      issueType,
      selectedHistoryOptions: issueType === 'all' ? [] : prev.selectedHistoryOptions,
    }));

    await sendFrontEvent('USER_TOUCH', {
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

    await sendFrontEvent('USER_TOUCH', {
      sessionId,
      action: 'TOGGLE_HISTORY_OPTION',
      option,
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

    await sendFrontEvent('SUBMIT_APPLICATION', payload);
    setStatusMessage('접수 요청을 전송했습니다.');
  };

  const renderScreen = () => {
    switch (screen) {
      case STEP_MAIN:
        return (
          <MainScreen
            categories={categories}
            onSelectService={handleMainServiceClick}
            onAccessibilityAction={handleAccessibilityAction}
            accessibility={accessibility}
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

      default:
        return null;
    }
  };

  return (
    <div className="app-shell">
      <ScreenFrame accessibility={accessibility}>
        {renderScreen()}
        {statusMessage ? <div className="status-message">{statusMessage}</div> : null}
        {submittedApplicationNo ? (
          <div className="status-message">신청번호: {submittedApplicationNo}</div>
        ) : null}
      </ScreenFrame>
    </div>
  );
}