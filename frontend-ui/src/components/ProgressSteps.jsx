export const DEFAULT_STEP_LABELS = ['신청서비스', '본인확인', '신청내용', '신청내용 및 수수료 확인'];

export default function ProgressSteps({ currentStep = 1, labels = DEFAULT_STEP_LABELS }) {
  const totalSteps = labels.length;

  return (
    <div className="progress-steps" aria-label={`전체 ${totalSteps}단계 중 ${currentStep}단계 진행 중`}>
      {labels.map((label, index) => {
        const stepNumber = index + 1;
        const state = stepNumber < currentStep ? 'completed' : stepNumber === currentStep ? 'current' : 'upcoming';

        return (
          <span
            key={`${label}-${stepNumber}`}
            className={`step-dot ${state}`}
            aria-label={`${stepNumber}단계 ${label}${state === 'current' ? ', 현재 단계' : ''}`}
          />
        );
      })}
    </div>
  );
}
