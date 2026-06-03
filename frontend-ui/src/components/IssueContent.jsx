import FlowHeader from './FlowHeader';
import BottomActions from './BottomActions';
import Keypad from './Keypad';

function RadioCircle({ checked }) {
  return <span className={`fake-radio ${checked ? 'checked' : ''}`} aria-hidden="true" />;
}

function CheckSquare({ checked }) {
  return <span className={`fake-checkbox ${checked ? 'checked' : ''}`} aria-hidden="true" />;
}

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
      <section className="content-panel resident-panel resident-issue-panel">
        <FlowHeader title="신청내용을 선택/입력 해주세요." currentStep={3} />

        <div className="content-body-frame body-left-frame resident-body">
          <section className="resident-card resident-issue-card">
            <h3 className="resident-card-title">주민등록표 발급형태 선택</h3>
            <p className="resident-sub-label">발급할 내용을 선택해주세요. <span>(필수)</span></p>

            <div className="resident-option-list">
              <button
                type="button"
                className={`resident-option-button ${issueType === 'all' ? 'selected' : ''}`}
                onClick={() => onIssueTypeChange('all')}
                aria-pressed={issueType === 'all'}
              >
                <RadioCircle checked={issueType === 'all'} />
                <span>전체발급</span>
              </button>

              <button
                type="button"
                className={`resident-option-button ${issueType === 'select' ? 'selected' : ''}`}
                onClick={() => onIssueTypeChange('select')}
                aria-pressed={issueType === 'select'}
              >
                <RadioCircle checked={issueType === 'select'} />
                <span>선택발급</span>
              </button>
            </div>

            {issueType === 'select' ? (
              <div className="resident-checkbox-list" aria-label="선택발급 포함 항목">
                {options.map((option, index) => {
                  const optionId = `${option}-${index}`;
                  const checked = selectedOptions.includes(optionId);

                  return (
                    <button
                      key={optionId}
                      type="button"
                      className={`resident-check-row ${checked ? 'selected' : ''}`}
                      onClick={() => onToggleOption(optionId)}
                      aria-pressed={checked}
                    >
                      <CheckSquare checked={checked} />
                      <span>{option}</span>
                    </button>
                  );
                })}
              </div>
            ) : null}
          </section>
        </div>
      </section>

      <BottomActions onHome={onHome} onPrev={onPrev} onNext={onNext} disableNext={disableNext} />
    </>
  );
}

export function CopyCountPage({ copyCount, onKeypadPress, onHome, onPrev, onNext }) {
  return (
    <>
      <section className="content-panel resident-panel resident-copy-panel">
        <FlowHeader title="신청내용을 선택/입력 해주세요." currentStep={3} />

        <div className="content-body-frame body-left-frame resident-body">
          <section className="resident-card resident-copy-card">
            <h3 className="resident-card-title">주민등록표 발급부수 입력</h3>

            <div className="resident-field-block">
              <label className="resident-field-label">발급부수 <span>(필수)</span></label>
              <div className="resident-copy-count-row">
                <div className="count-input resident-count-input">{copyCount || ''}</div>
                <span className="resident-count-unit">부</span>
              </div>
            </div>

            <div className="resident-keypad-wrap resident-copy-keypad-wrap">
              <Keypad onPress={onKeypadPress} />
            </div>
          </section>
        </div>
      </section>

      <BottomActions onHome={onHome} onPrev={onPrev} onNext={onNext} disableNext={!copyCount || Number(copyCount) < 1} />
    </>
  );
}
