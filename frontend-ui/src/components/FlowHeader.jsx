import ProgressSteps, { DEFAULT_STEP_LABELS } from './ProgressSteps';

export default function FlowHeader({ currentStep = 1, labels = DEFAULT_STEP_LABELS }) {
  const stepTitle = labels[currentStep - 1] || '';

  return (
    <header className="flow-header">
      {stepTitle ? <h2 className="flow-step-title">{stepTitle}</h2> : null}
      <ProgressSteps currentStep={currentStep} labels={labels} />
    </header>
  );
}
