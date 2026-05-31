export default function VoicePanel({
  active,
  listening,
  supported,
  transcript,
  guideText,
  error,
  onMicClick,
  onClose,
}) {
  if (!active) return null;

  const statusText = !supported ? '지원 안 됨' : listening ? '듣는 중' : '대기 중';

  return (
    <aside className="voice-panel compact" aria-live="polite">
      <button
        type="button"
        className={`voice-orb ${listening ? 'listening' : ''}`}
        onClick={onMicClick}
        aria-label={listening ? '음성 듣기 중지' : '음성 다시 듣기'}
      >
        <span className="voice-orb-icon" aria-hidden="true" />
      </button>

      <div className="voice-panel-text">
        <p className="voice-panel-topline">
          <span className={`voice-status-dot ${listening ? 'on' : ''}`} aria-hidden="true" />
          <strong>{statusText}</strong>
        </p>

        {guideText ? <p className="voice-guide-text">{guideText}</p> : null}
        {transcript ? (
          <p className="voice-transcript-text">
            <span>인식된 말</span>
            {transcript}
          </p>
        ) : null}
        {error ? <p className="voice-error-text">{error}</p> : null}
      </div>

      <button type="button" className="voice-panel-close" onClick={onClose}>
        닫기
      </button>
    </aside>
  );
}
