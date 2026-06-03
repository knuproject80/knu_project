import FlowHeader from './FlowHeader';
import BottomActions from './BottomActions';

function cleanSelectedOptions(options = []) {
  return options.map((item) => item.replace(/-\d+$/, ''));
}

function formatWon(value) {
  return Number(value || 0).toLocaleString('ko-KR');
}

export default function ConfirmFee({ summary, fee, totalFee, onHome, onPrev, onSubmit }) {
  const cleanedOptions = cleanSelectedOptions(summary.selectedOptions);
  const isSelectIssue = summary.issueTypeLabel === '선택발급';
  const copyCount = summary.copyCount || '1';

  return (
    <>
      <section className="content-panel resident-panel resident-confirm-panel">
        <FlowHeader title="신청내용 및 수수료를 확인해주세요." currentStep={4} />

        <div className="content-body-frame body-left-frame resident-body">
          <section className="resident-card resident-confirm-card">
            <h3 className="resident-card-title">신청내용 및 수수료 확인</h3>

            <div className="resident-summary-grid">
              <div className="resident-summary-block">
                <h4>신청 서비스</h4>
                <p>
                  <strong>서비스명</strong>
                  <span>{summary.serviceName}</span>
                </p>
              </div>

              <div className="resident-summary-block">
                <h4>본인확인 정보</h4>
                <p>
                  <strong>주민등록번호</strong>
                  <span>{summary.residentNumber || '입력 완료'}</span>
                </p>
              </div>

              <div className="resident-summary-block">
                <h4>신청내용</h4>
                <p>
                  <strong>발급형태</strong>
                  <span>{summary.issueTypeLabel}</span>
                </p>

                {isSelectIssue ? (
                  <ul>
                    {cleanedOptions.map((option, index) => (
                      <li key={`${option}-${index}`}>{option}</li>
                    ))}
                  </ul>
                ) : (
                  <p>
                    <strong>포함 항목</strong>
                    <span>전체 항목 포함</span>
                  </p>
                )}
              </div>

              <div className="resident-summary-block resident-fee-summary-block">
                <h4>발급 및 수수료</h4>
                <p>
                  <strong>발급부수</strong>
                  <span>{copyCount}부</span>
                </p>
                <p>
                  <strong>수수료 계산</strong>
                  <span>{formatWon(fee)}원 × {copyCount}장</span>
                </p>
                <p>
                  <strong>합계 수수료</strong>
                  <span className="resident-total-fee-text">{formatWon(totalFee)}원</span>
                </p>
              </div>
            </div>
          </section>
        </div>
      </section>

      <BottomActions onHome={onHome} onPrev={onPrev} onNext={onSubmit} nextLabel="제출" />
    </>
  );
}
