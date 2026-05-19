import { SERVICE_CHOICES } from '../data/options';
import ProgressSteps from './ProgressSteps';
import BottomActions from './BottomActions';

export default function ServiceSelect({ selectedServiceId, onSelect, onHome, onPrev, onNext }) {
  return (
    <>
      <section className="content-panel centered-panel">
        <h2 className="section-title">신청할 서비스를 선택하세요.</h2>
        <ProgressSteps currentStep={1} />

        <div className="content-body-frame body-center-frame">
          <div className="large-choice-list service-choice-list">
            {SERVICE_CHOICES.map((service) => (
              <button
                key={service.id}
                type="button"
                className={`large-choice-button ${selectedServiceId === service.id ? 'selected' : ''}`}
                onClick={() => onSelect(service)}
              >
                {service.label}
              </button>
            ))}
          </div>
        </div>
      </section>

      <BottomActions onHome={onHome} onPrev={onPrev} onNext={onNext} disableNext={!selectedServiceId} />
    </>
  );
}