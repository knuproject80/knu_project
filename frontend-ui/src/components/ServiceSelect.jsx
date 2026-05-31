import { SERVICE_CHOICES } from '../data/options';
import FlowHeader from './FlowHeader';
import BottomActions from './BottomActions';

export default function ServiceSelect({ selectedServiceId, onSelect, onHome, onPrev, onNext }) {
  return (
    <>
      <section className="content-panel resident-panel resident-service-panel">
        <FlowHeader title="신청할 서비스를 선택하세요." currentStep={1} />

        <div className="content-body-frame body-left-frame resident-body">
          <section className="resident-card resident-service-card">
            <h3 className="resident-card-title">신청할 서비스 선택</h3>

            <div className="resident-choice-list">
              {SERVICE_CHOICES.map((service) => (
                <button
                  key={service.id}
                  type="button"
                  className={`resident-choice-button ${selectedServiceId === service.id ? 'selected' : ''}`}
                  onClick={() => onSelect(service)}
                >
                  <span>{service.label}</span>
                </button>
              ))}
            </div>
          </section>
        </div>
      </section>

      <BottomActions onHome={onHome} onPrev={onPrev} onNext={onNext} disableNext={!selectedServiceId} />
    </>
  );
}
