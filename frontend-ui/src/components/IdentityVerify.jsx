import ProgressSteps from './ProgressSteps';
import BottomActions from './BottomActions';
import Keypad from './Keypad';

export default function IdentityVerify({ residentFront, residentBack, onKeypadPress, onHome, onPrev, onNext }) {
  return (
    <>
      <section className="content-panel identity-panel">
        <h2 className="section-title">본인확인을 해주세요.</h2>
        <ProgressSteps currentStep={2} />

        <div className="content-body-frame body-center-frame">
          <div className="field-block compact-top-gap">
            <label className="field-label">주민등록번호 입력</label>
            <div className="resident-input-row">
              <div className="masked-input">{residentFront}</div>
              <span className="hyphen">-</span>
              <div className="masked-input">{residentBack}</div>
            </div>
          </div>

          <Keypad onPress={onKeypadPress} />
        </div>
      </section>

      <BottomActions
        onHome={onHome}
        onPrev={onPrev}
        onNext={onNext}
        disableNext={residentFront.length !== 6 || residentBack.length !== 7}
      />
    </>
  );
}