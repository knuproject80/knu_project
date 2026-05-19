import ProgressSteps from './ProgressSteps';
import BottomActions from './BottomActions';
import Keypad from './Keypad';

export function IssueContentPage({
  issueType,
  options,
  selectedOptions,
  onIssueTypeChange,
  onToggleOption,
  onHome,
  onPrev,
  onNext,
}) {
  const disableNext = !issueType || (issueType === 'select' && selectedOptions.length === 0);

  return (
    <>
      <section className="content-panel">
        <h2 className="section-title">신청내용을 선택/입력 해주세요.</h2>
        <ProgressSteps currentStep={3} />

        <div className="content-body-frame body-left-frame">
          <div className="field-block compact-top-gap">
            <label className="field-label">발급형태 선택</label>
            <div className="radio-list">
              <label className="radio-item">
                <input
                  type="radio"
                  name="issueType"
                  checked={issueType === 'all'}
                  onChange={() => onIssueTypeChange('all')}
                />
                전체발급
              </label>
              <label className="radio-item">
                <input
                  type="radio"
                  name="issueType"
                  checked={issueType === 'select'}
                  onChange={() => onIssueTypeChange('select')}
                />
                선택발급
              </label>
            </div>
          </div>

          {issueType === 'select' ? (
            <div className="checkbox-box">
              {options.map((option, index) => (
                <label key={`${option}-${index}`} className="checkbox-item">
                  <input
                    type="checkbox"
                    checked={selectedOptions.includes(`${option}-${index}`)}
                    onChange={() => onToggleOption(`${option}-${index}`)}
                  />
                  {option}
                </label>
              ))}
            </div>
          ) : null}
        </div>
      </section>

      <BottomActions onHome={onHome} onPrev={onPrev} onNext={onNext} disableNext={disableNext} />
    </>
  );
}

export function CopyCountPage({ copyCount, onKeypadPress, onHome, onPrev, onNext }) {
  return (
    <>
      <section className="content-panel identity-panel">
        <h2 className="section-title">신청내용을 선택/입력 해주세요.</h2>
        <ProgressSteps currentStep={3} />

        <div className="content-body-frame body-center-frame">
          <div className="field-block compact-top-gap">
            <label className="field-label">발급부수 입력</label>
            <div className="copy-count-row">
              <div className="count-input">{copyCount || ''}</div>
              <span className="count-unit">부</span>
            </div>
          </div>

          <div className="copy-keypad-wrap">
            <Keypad onPress={onKeypadPress} />
          </div>
        </div>
      </section>

      <BottomActions onHome={onHome} onPrev={onPrev} onNext={onNext} disableNext={!copyCount || Number(copyCount) < 1} />
    </>
  );
}