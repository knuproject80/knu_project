# Kiosk AI Server (ai-server)

관공서 키오스크를 위한 AI/LLM 서버입니다.  
사용자의 자연어 입력(음성/텍스트)을 분석하여 **사용자 유형 분류**, **민원 서비스 추천**, **통합 분석** 결과를 JSON 형태로 반환합니다.

AI 서버는 화면을 직접 제어하지 않고, MCP Client 또는 Spring에서 사용할 수 있는 구조화된 추천 결과를 제공합니다.

---

## 1. 개요 (Overview)

이 서버는 키오스크 시스템에서 다음 역할을 담당합니다.

- 사용자 입력 분석
- 사용자 유형 분류
- 민원 서비스 추천
- 사용자 유형 + 서비스 통합 분석
- OpenAI API 기반 LLM 호출
- 명확한 민원 키워드에 대한 rule-based 우선 처리
- JSON 형태의 구조화된 응답 반환

현재 기본 흐름은 다음과 같습니다.

```text
사용자 입력
   ↓
AI Server
   ↓
1차: rule-based 매칭
   ↓  매칭 실패 시
2차: OpenAI LLM 분석
   ↓
JSON 응답 반환
```

---

## 2. 아키텍처 (Architecture)

```text
[Frontend / Voice Input]
        ↓
    MCP Client
        ↓
     AI Server (this)
        ↓
 Structured JSON Response
        ↓
    MCP Client / Spring
        ↓
   UI 업데이트 (화면 이동, 접근성 적용)
```

AI 서버는 최종 UI 이동을 직접 수행하지 않습니다.  
대신 `serviceId`, `userType`, `confidence`, `answer` 값을 반환하고, 실제 화면 이동 및 접근성 적용은 MCP Client 또는 Spring/Front에서 처리합니다.

---

## 3. 프로젝트 구조 (Project Structure)

```text
ai-server/
├─ app/
│  ├─ main.py                  # FastAPI 진입점 및 API 라우팅
│  ├─ config.py                # 환경설정 (모델, timeout, threshold 등)
│  ├─ model.py                 # OpenAI 호출 및 JSON 파싱
│  ├─ prompts.py               # LLM 프롬프트 정의
│  ├─ llm_schemas.py           # LLM 구조화 출력용 JSON Schema
│  ├─ schemas.py               # 요청/응답 스키마 (Pydantic)
│  ├─ catalog.py               # 민원 서비스 카탈로그 및 키워드 매핑
│  ├─ exceptions.py            # 커스텀 예외
│  └─ services/
│     ├─ user_type.py          # 사용자 유형 분류 로직
│     ├─ service_recommend.py  # 서비스 추천 로직
│     └─ analyze.py            # 사용자 유형 + 서비스 통합 분석 로직
│
├─ tests/
│  └─ test_requests.json       # 테스트 요청 예시
│
├─ requirements.txt
├─ .env.example
├─ run.sh
└─ README.md
```

---

## 4. 설치 및 실행 (Setup & Run)

### 1) Python 환경

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
```

### 2) 패키지 설치

```bash
pip install -r requirements.txt
```

### 3) 환경변수 설정

#### macOS / Linux

```bash
export OPENAI_API_KEY=your_api_key
```

#### Windows PowerShell

```powershell
$env:OPENAI_API_KEY="your_api_key"
```

선택 옵션:

```bash
export OPENAI_MODEL=gpt-5-mini
export OPENAI_TIMEOUT=20
export OPENAI_MAX_OUTPUT_TOKENS=1000
export USER_TYPE_CONFIDENCE_THRESHOLD=0.60
export SERVICE_CONFIDENCE_THRESHOLD=0.60
export CONFIRMATION_CONFIDENCE_THRESHOLD=0.85
```

Windows PowerShell에서는 다음과 같이 설정할 수 있습니다.

```powershell
$env:OPENAI_MODEL="gpt-5-mini"
$env:OPENAI_TIMEOUT="20"
$env:OPENAI_MAX_OUTPUT_TOKENS="1000"
$env:USER_TYPE_CONFIDENCE_THRESHOLD="0.60"
$env:SERVICE_CONFIDENCE_THRESHOLD="0.60"
$env:CONFIRMATION_CONFIDENCE_THRESHOLD="0.85"
```

`.env.example` 파일을 참고하여 필요한 환경변수를 확인할 수 있습니다.

### 4) 서버 실행

```bash
uvicorn app.main:app --reload
```

또는

```bash
bash run.sh
```

정상 실행 시 다음과 같은 로그가 출력됩니다.

```text
[AI] OpenAI client ready: gpt-5-mini
Application startup complete.
```

---

## 5. API 명세 (API Endpoints)

### 5.1 Health Check

```http
GET /health
```

응답:

```json
{
  "status": "ok",
  "model": "gpt-5-mini",
  "version": "1.2.0"
}
```

---

### 5.2 사용자 유형 분류

```http
POST /classify/user-type
```

요청:

```json
{
  "text": "글씨가 잘 안 보여요"
}
```

응답:

```json
{
  "task": "classify_user_type",
  "success": true,
  "fallback_used": false,
  "userType": "VISUAL_IMPAIRMENT",
  "confidence": 0.95,
  "reason": "글씨가 잘 안 보인다고 직접 언급했다.",
  "source": "rule_based",
  "raw_text": "{...}",
  "model_name": "rule_based"
}
```

설명:

- 명확한 표현은 rule-based로 먼저 처리합니다.
- rule-based로 판단하기 어려운 경우 OpenAI LLM을 호출합니다.
- confidence가 threshold 미만이면 `UNKNOWN`으로 처리됩니다.

---

### 5.3 서비스 추천

```http
POST /classify/service
```

요청:

```json
{
  "text": "주민등록등본 발급하고 싶어요"
}
```

응답:

```json
{
  "task": "recommend_service",
  "success": true,
  "fallback_used": false,
  "intent": "issue_document",
  "serviceId": "RESIDENT_REGISTRATION_COPY",
  "confidence": 0.99,
  "answer": "주민등록등본 발급 메뉴로 안내할게요.",
  "needsConfirmation": false,
  "source": "rule_based",
  "raw_text": "{...}",
  "model_name": "rule_based"
}
```

설명:

- `등본`, `가족관계증명서`, `전입신고`처럼 명확한 민원 키워드는 rule-based로 처리합니다.
- rule-based에 걸리지 않는 애매한 입력은 OpenAI LLM으로 분석합니다.
- confidence가 낮은 경우 `serviceId`는 `UNKNOWN`으로 반환됩니다.

---

### 5.4 통합 분석

```http
POST /analyze
```

`/analyze`는 사용자 유형 분류와 서비스 추천을 한 번에 수행하는 API입니다.

요청:

```json
{
  "text": "글씨가 잘 안 보이는데 주민등록등본 발급하고 싶어요"
}
```

응답:

```json
{
  "task": "analyze",
  "success": true,
  "fallback_used": false,
  "userType": "VISUAL_IMPAIRMENT",
  "userTypeConfidence": 0.95,
  "intent": "issue_document",
  "serviceId": "RESIDENT_REGISTRATION_COPY",
  "serviceConfidence": 0.99,
  "answer": "주민등록등본 발급 메뉴로 안내할게요.",
  "needsConfirmation": false,
  "source": "rule_based",
  "model_name": "rule_based"
}
```

사용 목적:

- 음성 입력 한 문장 안에 접근성 요구와 민원 요청이 같이 들어오는 경우 처리
- MCP Client에서 API 호출 횟수를 줄이고 싶을 때 사용
- 사용자 유형과 서비스 추천을 동시에 판단해야 하는 시나리오에 사용

---

## 6. 사용자 유형 (User Types)

| 값 | 설명 |
| --- | --- |
| ELDERLY | 고령 사용자 |
| WHEELCHAIR | 휠체어 사용자 |
| VISUAL_IMPAIRMENT | 시각 장애 또는 시각 불편 |
| HEARING_IMPAIRMENT | 청각 장애 또는 청각 불편 |
| NORMAL | 일반 사용자 |
| UNKNOWN | 불확실 |

---

## 7. 서비스 ID (Service IDs)

| 값 | 설명 |
| --- | --- |
| RESIDENT_REGISTRATION_COPY | 주민등록등본 |
| FAMILY_CERTIFICATE | 가족관계증명서 |
| MOVE_IN_REPORT | 전입신고 |
| HEALTH_INSURANCE | 건강보험 관련 |
| MARRIAGE_CERTIFICATE | 혼인관계증명서 |
| TAX_CERTIFICATE | 세금 납부 확인 |
| UNKNOWN | 불확실 |

서비스 ID와 키워드 매핑은 `app/catalog.py`에서 관리합니다.

---

## 8. Intent 값

| 값 | 설명 |
| --- | --- |
| issue_document | 증명서 발급 |
| submit_application | 신고/신청 |
| pay_or_check | 납부 또는 확인 |
| welfare_service | 복지 서비스 |
| general_question | 일반 질문 |
| unknown | 불확실 |

---

## 9. Confidence 정책

| 범위 | 처리 방식 |
| --- | --- |
| ≥ 0.85 | 바로 추천 가능 |
| 0.60 ~ 0.84 | 중간 신뢰도, 확인 질문 권장 |
| < 0.60 | UNKNOWN 처리 |

`needsConfirmation` 값은 confidence 기준으로 설정됩니다.

- confidence가 충분히 높으면 `false`
- confidence가 낮거나 애매하면 `true`

---

## 10. Rule-based + LLM 처리 방식

서비스 추천과 사용자 유형 분류는 다음 순서로 처리합니다.

```text
1. 입력 텍스트 정규화
2. catalog.py 또는 규칙 기반 키워드 매칭
3. 매칭 성공 시 즉시 JSON 반환
4. 매칭 실패 시 OpenAI LLM 호출
5. LLM 응답 검증
6. confidence threshold 적용
7. 최종 JSON 반환
```

이 방식을 사용하는 이유는 다음과 같습니다.

- 명확한 민원 요청은 LLM 오분류를 줄일 수 있음
- 애매한 표현은 LLM으로 유연하게 처리 가능
- MCP/Spring/Front에서 사용할 응답 형식을 안정적으로 유지 가능

---

## 11. 에러 및 fallback 처리

다음 상황에서 fallback이 발생합니다.

- OpenAI API 실패
- OpenAI API timeout
- JSON 파싱 실패
- 잘못된 응답 형식
- confidence threshold 미만
- 알 수 없는 serviceId 또는 userType 반환

fallback 예시:

```json
{
  "task": "recommend_service",
  "success": false,
  "fallback_used": true,
  "intent": "unknown",
  "serviceId": "UNKNOWN",
  "confidence": 0.0,
  "answer": "서비스 추천에 실패했습니다.",
  "needsConfirmation": true,
  "source": "fallback",
  "raw_text": "",
  "model_name": "gpt-5-mini"
}
```

---

## 12. 테스트 방법

### 1) Swagger UI

서버 실행 후 브라우저에서 접속합니다.

```text
http://127.0.0.1:8000/docs
```

Swagger UI에서 각 API를 직접 테스트할 수 있습니다.

### 2) PowerShell 테스트

PowerShell에서 한글 요청이 깨질 수 있으므로 UTF-8 설정 후 테스트합니다.

```powershell
chcp 65001
[Console]::InputEncoding  = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$OutputEncoding = [System.Text.UTF8Encoding]::new()
```

요청 예시:

```powershell
$body = @{ text = "주민등록등본 발급하고 싶어요" } | ConvertTo-Json
$utf8 = [System.Text.Encoding]::UTF8.GetBytes($body)

Invoke-RestMethod -Uri "http://127.0.0.1:8000/classify/service" `
  -Method POST `
  -ContentType "application/json; charset=utf-8" `
  -Body $utf8
```

### 3) 테스트 입력 예시

```json
{
  "service": [
    { "text": "주민등록등본 발급하고 싶어요" },
    { "text": "전입신고 하러 왔어요" },
    { "text": "가족관계증명서 필요해요" },
    { "text": "세금 납부 확인서 발급하고 싶어요" }
  ],
  "userType": [
    { "text": "글씨가 잘 안 보여요" },
    { "text": "휠체어 이용자입니다" },
    { "text": "소리가 잘 안 들려요" }
  ],
  "analyze": [
    { "text": "글씨가 잘 안 보이는데 주민등록등본 발급하고 싶어요" }
  ]
}
```

---

## 13. 연동 시 참고 사항

MCP Client 또는 Spring에서 AI 서버를 호출할 때는 다음 값을 중심으로 사용합니다.

- `serviceId`: 이동할 민원 서비스 식별자
- `userType`: 적용할 접근성 사용자 유형
- `confidence`: 추천 신뢰도
- `needsConfirmation`: 사용자 확인 필요 여부
- `answer`: 사용자에게 표시하거나 음성 안내할 문장

예시 처리 흐름:

```text
AI Server 응답 수신
   ↓
serviceId 확인
   ↓
UNKNOWN이 아니면 해당 서비스 화면 이동
   ↓
userType 확인
   ↓
접근성 UI 설정 적용
```

---

## 14. 보안 주의사항

- OpenAI API Key는 코드나 README에 직접 작성하지 않습니다.
- `.env`, 실제 API Key 파일은 Git에 올리지 않습니다.
- 키가 노출된 경우 즉시 폐기하고 새 키를 발급받아야 합니다.
- Git에는 `.env.example`처럼 예시 파일만 포함합니다.

---

## 15. 향후 개선 사항

- 민원 서비스 종류 추가
- 서비스 카탈로그 키워드 보강
- MCP Client와 실제 연동 테스트
- 전체 키오스크 시나리오 기반 통합 테스트
- 디버그 로그 정리 및 운영용 로깅 구조 적용

---

## 16. 핵심 설계 방향

이 서버는 챗봇처럼 긴 답변을 생성하는 서버가 아니라,  
키오스크 제어에 필요한 값을 안정적으로 뽑아내는 **분류/추천 서버**입니다.

따라서 최종 목표는 다음과 같습니다.

```text
자연어 입력 → 사용자 유형 / 민원 서비스 / confidence → JSON 응답
```

