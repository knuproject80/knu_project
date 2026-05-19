import ProgressSteps from './ProgressSteps';
import BottomActions from './BottomActions';

function cleanSelectedOptions(options = []) {
  return options.map((item) => item.replace(/-\d+$/, ''));
}

export default function ConfirmFee({ summary, fee, totalFee, onHome, onPrev, onSubmit }) {
  const cleanedOptions = cleanSelectedOptions(summary.selectedOptions);

  return (
    <>
      <section className="content-panel confirm-panel">
        <h2 className="section-title">신청내용 및 수수료를 확인해주세요.</h2>
        <ProgressSteps currentStep={4} />

        <div className="content-body-frame body-left-frame">
          <div className="summary-block">
            <label className="field-label">신청 서비스</label>
            <div className="summary-input">{summary.serviceName}</div>
          </div>

          <div className="summary-block">
            <label className="field-label">신청내용</label>
            <div className="summary-textarea">
              {summary.issueTypeLabel}
              {cleanedOptions.length ? (
                <>
                  <br />
                  {cleanedOptions.join('\n')}
                </>
              ) : null}
            </div>
          </div>

          <div className="summary-block small-gap">
            <label className="field-label">발급 부수</label>
            <div className="small-count-box">{summary.copyCount}</div>
          </div>

          <div className="summary-block fee-block">
            <label className="field-label">수수료</label>
            <div className="fee-row">
              <span>1장 당</span>

              <div className="small-count-box">400</div>
              <span>원</span>

              <span>x</span>

              <div className="small-count-box">{summary.copyCount}</div>
              <span>장</span>
            </div>
          </div>

          <div className="total-fee">
            합계 수수료:
            <div className="small-count-box total-box">
              {totalFee}
            </div>
            <span>원</span>
          </div>
        </div>
      </section>

      <BottomActions onHome={onHome} onPrev={onPrev} onNext={onSubmit} nextLabel="제출" />
    </>
  );
}