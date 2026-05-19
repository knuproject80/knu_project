export default function BottomActions({ onHome, onPrev, onNext, nextLabel = '다음', disablePrev, disableNext }) {
  return (
    <div className="bottom-actions">
      <button type="button" className="pill-button primary" onClick={onHome}>
        메인으로
      </button>
      <div className="bottom-actions-right">
        <button type="button" className="pill-button" onClick={onPrev} disabled={disablePrev}>
          이전
        </button>
        <button
          type="button"
          className={`pill-button ${nextLabel === '제출' ? 'submit-button' : ''}`}
          onClick={onNext}
          disabled={disableNext}
        >
          {nextLabel}
        </button>
      </div>
    </div>
  );
}
