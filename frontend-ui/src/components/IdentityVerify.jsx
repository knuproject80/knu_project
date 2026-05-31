import FlowHeader from './FlowHeader';
import BottomActions from './BottomActions';
import Keypad from './Keypad';

export default function IdentityVerify({ residentFront, residentBack, onKeypadPress, onHome, onPrev, onNext }) {
  return (
    <>
      <section className="content-panel resident-panel resident-identity-panel">
        <FlowHeader title="본인확인을 해주세요." currentStep={2} />

        <div className="content-body-frame body-left-frame resident-body">
          <section className="resident-card resident-identity-card">
            <h3 className="resident-card-title">주민등록번호 본인확인</h3>

            <div className="resident-field-block">
              <label className="resident-field-label">주민등록번호 입력 <span>(필수)</span></label>
              <div className="resident-number-row">
                <div className="masked-input resident-number-input" aria-label="주민등록번호 앞자리">
                  {residentFront}
                </div>
                <span className="resident-hyphen">-</span>
                <div className="masked-input resident-number-input" aria-label="주민등록번호 뒷자리">
                  {'●'.repeat(residentBack.length)}
                </div>
              </div>
            </div>

            <div className="resident-keypad-wrap">
              <Keypad onPress={onKeypadPress} />
            </div>
          </section>
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
