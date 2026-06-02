# AI Server v6.3 patch

주요 반영 사항:

- `/chat` 요청 `mode` 파라미터 지원
  - `mode="classify"` 또는 누락: 기존 VOICE_INPUT 의도 분류
  - `mode="step_guide"`: STEP_CHANGE 단계 안내 전용, `answer` 중심 응답
- `mode="classify"` 응답에 `entities` 필수 포함
  - `count`, `paymentMethod`, `purpose`, `scope`
- 다중 발화 처리
  - 예: `주민등록등본 1개 현금으로 발급`
  - `entities.count=1`, `entities.paymentMethod="CASH"`
- v6.2/v6.3 step key 동기화
  - `CERTIFICATE_SELECT_PURPOSE`, `CERTIFICATE_SELECT_RRN`
  - `MOVEIN_INPUT_BASIC_INFO`, `MOVEIN_SELECT_REASON`, `MOVEIN_SELECT_HOUSEHOLD`, `MOVEIN_SELECT_EXTRA_SERVICE`
- `step_guide`에서 의도 재질문 문구 금지
- `ELDERLY`, `WHEELCHAIR`, `retryCount` 기반 문구 보정

테스트:

```powershell
python tests\test_ai_server_v63_cases.py
python tests\test_ai_server_chat_mode_cases.py
python tests\test_ai_server_v61_cases.py
```

TC-AI-11은 AI Server 500/timeout 시 MCP Client가 GUIDE_TEXT로 폴백하는 통합 테스트입니다.
AI Server 단독 테스트에서는 직접 실패를 발생시키지 않고, MCP Client 쪽에서 확인해야 합니다.
