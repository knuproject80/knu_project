@echo off
chcp 65001 > nul
title KNU 배리어프리 키오스크 - 전체 서버 실행

echo =============================================
echo   KNU 배리어프리 키오스크 서버 시작
echo =============================================
echo.

if "%OPENAI_API_KEY%"=="" (
    echo [오류] OPENAI_API_KEY 가 설정되지 않았습니다.
    echo.
    echo cmd 창에서 아래 명령어를 먼저 실행하세요:
    echo   set OPENAI_API_KEY=sk-...실제키...
    echo.
    pause
    exit /b 1
)
echo [OK] OPENAI_API_KEY 확인 완료
echo.

set ROOT=%~dp0
set ROOT=%ROOT:~0,-1%

echo [1/5] PostgreSQL 서비스 시작 중...
net start postgresql-x64-18 > nul 2>&1
if %errorlevel%==0 (
    echo       [OK] PostgreSQL 시작 완료
) else (
    echo       [OK] PostgreSQL 이미 실행 중
)
echo.

echo [2/5] Backend (Spring Boot) 시작 중...
start "Backend - Spring Boot" cmd /k "cd /d %ROOT%\backend-spring && gradlew.bat bootRun"
timeout /t 3 /nobreak > nul
echo       [OK] Spring Boot 실행 중 ... (포트 8080)
echo.

echo [3/5] AI Server (FastAPI) 시작 중...
start "AI Server - FastAPI" cmd /k "cd /d %ROOT%\ai-server && (if not exist venv python -m venv venv) && call venv\Scripts\activate && pip install -r requirements.txt -q && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
timeout /t 3 /nobreak > nul
echo       [OK] AI Server 실행 중 ... (포트 8000)
echo.

echo [4/5] MCP Client 시작 중...
start "MCP Client" cmd /k "cd /d %ROOT%\mcp-server\mcp_client && (if not exist venv python -m venv venv) && call venv\Scripts\activate && pip install mcp -q && python main.py"
timeout /t 3 /nobreak > nul
echo       [OK] MCP Client 실행 중
echo.

echo [5/5] Frontend (Vite) 시작 중...
start "Frontend - Vite" cmd /k "cd /d %ROOT%\frontend-ui && npm install && npm run dev"
timeout /t 3 /nobreak > nul
echo       [OK] Frontend 실행 중 ... (포트 5173)
echo.

echo =============================================
echo   모든 서버가 시작되었습니다!
echo =============================================
echo.
echo   Backend        : http://localhost:8080
echo   Backend Swagger: http://localhost:8080/swagger-ui/index.html
echo   AI Server      : http://localhost:8000
echo   AI Swagger     : http://localhost:8000/docs
echo   Frontend       : http://localhost:5173
echo.
echo   종료하려면 각 창을 닫거나 Ctrl+C 를 누르세요.
echo =============================================
pause
