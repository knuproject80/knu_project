# Kiosk Frontend UI (frontend-ui)

관공서 키오스크를 위한 React 기반 프론트엔드입니다.  
사용자가 키오스크 화면에서 민원 서비스를 선택하고, 신청 정보를 입력하며, 접근성 모드를 적용한 상태로 서비스를 이용할 수 있도록 화면 UI와 사용자 인터랙션을 제공합니다.

프론트엔드는 화면 표시와 사용자 입력 처리, WebSocket/STOMP 기반 이벤트 송수신을 담당합니다.  
실제 민원 처리 로직, 세션 관리, AI 분석, MCP 제어 흐름은 Spring 서버, MCP 서버, AI 서버와 연동하여 처리합니다.

---

## 1. 개요 (Overview)

이 프론트엔드는 키오스크 시스템에서 다음 역할을 담당합니다.

- 메인 서비스 화면 제공
- 민원 서비스 선택 화면 제공
- 전입신고 등 단계별 신청 화면 제공
- 사용자 입력 폼 처리
- 화면 키보드 및 숫자 키패드 제공
- 고대비 모드, 큰글자 모드, 낮은화면 모드 등 접근성 UI 제공
- 음성 입력 및 음성 안내 버튼 UI 제공
- Spring 서버와 WebSocket/STOMP 연결
- MCP Client와 연동되는 프론트 이벤트 송신
- MCP/Spring에서 전달받은 UI 명령 처리

---

## 2. 실행 방법 (How to Run)

프로젝트 루트에서 `frontend-ui` 폴더로 이동합니다.

```bash
cd frontend-ui
```

필요한 패키지를 설치합니다.

```bash
npm install
```

개발 서버를 실행합니다.

```bash
npm run dev
```

실행 후 브라우저에서 Vite가 안내하는 주소로 접속합니다.

```bash
http://localhost:5173
```

---

## 3. 주요 폴더 구조 (Project Structure)

```txt
frontend-ui/
├─ public/
├─ src/
│  ├─ api/
│  ├─ components/
│  ├─ data/
│  ├─ styles/
│  ├─ App.jsx
│  ├─ index.css
│  └─ main.jsx
├─ index.html
├─ package.json
├─ package-lock.json
└─ vite.config.js
```

---

## 4. 폴더 설명

### public

정적 파일을 저장하는 폴더입니다.  
이미지, 아이콘 등 빌드 과정에서 별도 처리가 필요 없는 파일을 둘 수 있습니다.

### src

프론트엔드의 주요 소스 코드가 들어있는 폴더입니다.

### src/api

Spring 서버 또는 MCP 연동과 관련된 API, WebSocket 연결 코드를 관리합니다.

### src/components

화면을 구성하는 React 컴포넌트를 관리합니다.  
메인 화면, 서비스 선택 화면, 신청 단계 화면, 입력 컴포넌트 등이 포함됩니다.

### src/data

서비스 목록, 선택 옵션, 접근성 관련 옵션 등 화면에서 사용하는 데이터를 관리합니다.

### src/styles

화면 스타일과 접근성 모드 관련 CSS를 관리합니다.

### App.jsx

프론트엔드의 전체 화면 흐름과 주요 상태를 관리하는 최상위 컴포넌트입니다.

### main.jsx

React 앱을 브라우저에 렌더링하는 진입 파일입니다.

---

## 5. 환경 변수 (Environment Variables)

로컬 실행 시 WebSocket 서버 주소가 필요한 경우 `frontend-ui/.env` 파일을 생성합니다.

```env
VITE_WS_URL=ws://localhost:8080/ws
```

`.env` 파일은 개인 로컬 환경 설정이므로 GitHub에 올리지 않습니다.

---

## 6. WebSocket / STOMP 연동

프론트엔드는 Spring 서버의 WebSocket 엔드포인트와 연결하여 MCP Client와 이벤트를 주고받습니다.

기본 WebSocket 주소 예시는 다음과 같습니다.

```txt
ws://localhost:8080/ws
```

프론트엔드에서 담당하는 주요 역할은 다음과 같습니다.

- WebSocket 연결 생성
- STOMP 구독 등록
- 사용자 입력 이벤트 전송
- 화면 이동 또는 UI 제어 명령 수신
- MCP/Spring으로 ACK 응답 전송

프론트엔드는 민원 처리 결과를 직접 판단하지 않고, MCP Client 또는 Spring 서버에서 전달받은 명령에 따라 화면을 갱신합니다.

---

## 7. 서버 연동 구조

전체 시스템은 다음과 같은 구조로 동작합니다.

```txt
사용자
  ↓
frontend-ui
  ↓
Spring WebSocket Server
  ↓
MCP Client / MCP Server
  ↓
AI Server
```

프론트엔드는 사용자의 입력과 화면 이벤트를 서버로 전달합니다.  
서버와 MCP는 입력 내용을 분석하고, 필요한 화면 이동 또는 서비스 추천 결과를 다시 프론트엔드로 전달합니다.

---

## 8. GitHub 업로드 시 주의사항

다음 파일과 폴더는 GitHub에 올리지 않습니다.

```txt
node_modules/
dist/
.env
```

`node_modules`는 용량이 크고, 다른 개발자가 `npm install` 명령어로 다시 생성할 수 있으므로 저장소에 포함하지 않습니다.

---

## 9. 설치 및 실행 요약

```bash
cd frontend-ui
npm install
npm run dev
```