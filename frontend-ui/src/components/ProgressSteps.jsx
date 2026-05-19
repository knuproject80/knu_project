const STEP_LABELS = ['신청서비스', '본인확인', '신청내용', '신청내용 및 수수료 확인'];

export default function ProgressSteps({ currentStep = 1 }) {
  return (
    <div className="progress-steps">
      {STEP_LABELS.map((label, index) => {
        const stepNumber = index + 1;
        const state = currentStep >= stepNumber ? 'active' : 'inactive';
        return (
          <div key={label} className={`step-item ${state}`}>
            <div className="step-circle">{label}</div>
          </div>
        );
      })}
    </div>
  );
}
