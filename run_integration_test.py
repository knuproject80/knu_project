#!/usr/bin/env python3
# run_integration_test.py
"""
배리어프리 키오스크 — 통합테스트 단일 실행 런처
===============================================================

C:/knu_project/ 루트에 두고 실행하세요.

  [기동 순서]
    PostgreSQL(확인만)  →  Spring 백엔드  →  AI 서버(FastAPI)
        →  MCP 컨트롤러(main.py)  →  프론트엔드

  ※ mcp_server.py 는 mcp_client.py(main.py 내부)가 stdio 로 자동 기동하므로
    이 런처에서 따로 실행하지 않는다.

  [핵심]
    - 각 파이썬 컴포넌트는 자기 venv 인터프리터로 실행 (자동 탐지)
    - MCP 가 자식으로 띄우는 `python ./mcp_server.py` 도 venv 를 쓰도록 PATH 주입
    - 단계별 헬스체크(HTTP) 또는 로그패턴으로 준비 확인 후 다음 단계 기동
    - 모든 로그 [컴포넌트] 접두어로 합쳐 출력 + logs/<name>.log 저장
    - Ctrl+C 한 번에 역순 정리

사용법:
    python run_integration_test.py
    python run_integration_test.py --only ai,mcp
    python run_integration_test.py --skip frontend
"""

from __future__ import annotations

import argparse
import os
import re
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

IS_WIN = os.name == "nt"

# ══════════════════════════════════════════════════════════════════
#  CONFIG — knu_project 루트에 두면 그대로 동작. 다르면 경로만 수정.
# ══════════════════════════════════════════════════════════════════

ROOT = Path(__file__).resolve().parent          # = C:/knu_project

SPRING_DIR   = ROOT / "backend-spring"
AI_DIR       = ROOT / "ai-server"
MCP_DIR      = ROOT / "mcp-server" / "mcp_client"   # main.py 가 있는 폴더
FRONTEND_DIR = ROOT / "frontend-ui"

SPRING_PORT   = 8080        # config.WS_URL = ws://localhost:8080/ws
AI_PORT       = 8000        # config.AI_SERVER_BASE_URL = http://127.0.0.1:8000
FRONTEND_PORT = 5173        # ★ 프론트 스택 확인 필요 (Vite=5173 / CRA=3000 / Next=3000)
POSTGRES_PORT = 5432

GRADLEW = "gradlew.bat" if IS_WIN else "./gradlew"
NPM     = "npm.cmd" if IS_WIN else "npm"

# ══════════════════════════════════════════════════════════════════
#  venv 탐지
# ══════════════════════════════════════════════════════════════════

def _venv_python(project_dir: Path) -> str:
    """project_dir 아래 .venv / venv 에서 인터프리터를 찾는다. 없으면 현재 파이썬."""
    for name in (".venv", "venv"):
        cand = project_dir / name / ("Scripts/python.exe" if IS_WIN else "bin/python")
        if cand.exists():
            return str(cand)
    return sys.executable


def _venv_bin_dir(project_dir: Path) -> str | None:
    """자식 프로세스 PATH 앞에 끼워줄 venv 실행 디렉터리."""
    for name in (".venv", "venv"):
        d = project_dir / name / ("Scripts" if IS_WIN else "bin")
        if d.exists():
            return str(d)
    return None


# ══════════════════════════════════════════════════════════════════
#  컴포넌트 정의
# ══════════════════════════════════════════════════════════════════

@dataclass
class Component:
    name: str
    label: str
    cwd: Path
    command: list[str]
    env: dict[str, str] = field(default_factory=dict)
    path_prepend: str | None = None     # PATH 앞에 끼워넣을 디렉터리(venv)
    health_url: str | None = None
    ready_pattern: str | None = None
    startup_timeout: float = 90.0
    startup_delay: float = 0.0      # 준비 완료 후 추가 대기 (다음 단계 기동 전)
    enabled: bool = True

    proc: subprocess.Popen | None = None
    _ready: threading.Event = field(default_factory=threading.Event)
    _pattern_re: re.Pattern | None = None


def build_components() -> list[Component]:
    ai_python  = _venv_python(AI_DIR)
    mcp_python = _venv_python(MCP_DIR)
    mcp_bin    = _venv_bin_dir(MCP_DIR)   # 자식 mcp_server.py 가 쓸 venv

    return [
        Component(
            name="spring",
            label="SPRING",
            cwd=SPRING_DIR,
            command=[GRADLEW, "bootRun"],
            health_url=f"http://localhost:{SPRING_PORT}/actuator/health",
            ready_pattern=r"Started \w+Application in .* seconds",
            startup_timeout=180.0,
            startup_delay=5.0,   # STOMP 엔드포인트 안정화 대기
        ),
        Component(
            name="ai",
            label="AI",
            cwd=AI_DIR,
            command=[ai_python, "-m", "uvicorn", "app.main:app", "--port", str(AI_PORT)],
            health_url=f"http://localhost:{AI_PORT}/docs",
            ready_pattern=r"Application startup complete|OpenAI client ready",
            startup_timeout=60.0,
        ),
        Component(
            name="mcp",
            label="MCP",
            cwd=MCP_DIR,
            command=[mcp_python, "main.py"],
            path_prepend=mcp_bin,   # 내부 `python ./mcp_server.py` 가 venv 쓰도록
            env={
                "PYTHONUTF8": "1",          # Windows 한글 인코딩 문제 해결
                "PYTHONIOENCODING": "utf-8",
            },
            ready_pattern=r"/topic/front/ack",   # ASCII 패턴 (STOMP 구독 완료 시점)
            startup_timeout=45.0,
        ),
        Component(
            name="frontend",
            label="FRONT",
            cwd=FRONTEND_DIR,
            command=[NPM, "run", "dev"],
            ready_pattern=r"Local:\s+http|ready in|compiled successfully|VITE v",
            startup_timeout=120.0,
        ),
    ]


# ══════════════════════════════════════════════════════════════════
#  컬러 / 로깅
# ══════════════════════════════════════════════════════════════════

_COLORS = ["\033[36m", "\033[32m", "\033[33m", "\033[35m", "\033[34m", "\033[31m"]
_RESET = "\033[0m"
USE_COLOR = True


def _c(idx: int, text: str) -> str:
    return text if not USE_COLOR else f"{_COLORS[idx % len(_COLORS)]}{text}{_RESET}"


def info(msg: str) -> None:
    print(_c(0, f"[ orchestrator ] {msg}"), flush=True)


def warn(msg: str) -> None:
    print(_c(2, f"[ orchestrator ] {msg}"), flush=True)


def err(msg: str) -> None:
    print(_c(5, f"[ orchestrator ] {msg}"), flush=True)


# ══════════════════════════════════════════════════════════════════
#  기동 / 로그 펌프 / 헬스체크
# ══════════════════════════════════════════════════════════════════

LOG_DIR = ROOT / "logs"


def _pump_output(comp: Component, color_idx: int) -> None:
    LOG_DIR.mkdir(exist_ok=True)
    log_path = LOG_DIR / f"{comp.name}.log"
    prefix = _c(color_idx, f"[{comp.label:^6}]")

    assert comp.proc is not None and comp.proc.stdout is not None
    with open(log_path, "w", encoding="utf-8") as fp:
        for raw in comp.proc.stdout:
            line = raw.rstrip("\n")
            print(f"{prefix} {line}", flush=True)
            fp.write(line + "\n")
            fp.flush()
            if comp._pattern_re and not comp._ready.is_set():
                if comp._pattern_re.search(line):
                    comp._ready.set()


def _http_ok(url: str, timeout: float = 3.0) -> bool:
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method="GET"), timeout=timeout) as resp:
            return 200 <= resp.status < 400
    except urllib.error.HTTPError as e:
        return e.code < 500           # 404/405 라도 서버는 떠 있음
    except Exception:
        return False


def _port_open(port: int, host: str = "127.0.0.1", timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def start_component(comp: Component, color_idx: int) -> bool:
    if not comp.cwd.exists():
        err(f"'{comp.name}' 디렉터리 없음: {comp.cwd}  → CONFIG 경로 확인")
        return False

    info(f"'{comp.name}' 기동: {' '.join(comp.command)}  (cwd={comp.cwd})")

    env = os.environ.copy()
    env.update(comp.env)
    env.setdefault("PYTHONUNBUFFERED", "1")
    if comp.path_prepend:
        env["PATH"] = comp.path_prepend + os.pathsep + env.get("PATH", "")

    if comp.ready_pattern:
        comp._pattern_re = re.compile(comp.ready_pattern)

    try:
        comp.proc = subprocess.Popen(
            comp.command,
            cwd=str(comp.cwd),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            shell=IS_WIN,           # .bat/.cmd 실행용
        )
    except FileNotFoundError as e:
        err(f"'{comp.name}' 실행 파일 없음: {e}")
        return False

    threading.Thread(target=_pump_output, args=(comp, color_idx), daemon=True).start()
    return True


def wait_until_ready(comp: Component) -> bool:
    deadline = time.time() + comp.startup_timeout
    info(f"'{comp.name}' 준비 대기 중... (최대 {comp.startup_timeout:.0f}s)")

    while time.time() < deadline:
        if comp.proc and comp.proc.poll() is not None:
            err(f"'{comp.name}' 조기 종료 (exit={comp.proc.returncode}) → logs/{comp.name}.log 확인")
            return False
        if comp._ready.is_set():
            info(f"'{comp.name}' 준비 완료 (로그 패턴 감지)")
            if comp.startup_delay > 0:
                info(f"'{comp.name}' 안정화 대기 {comp.startup_delay:.0f}s...")
                time.sleep(comp.startup_delay)
            return True
        if comp.health_url and _http_ok(comp.health_url):
            info(f"'{comp.name}' 준비 완료 (헬스체크 OK)")
            if comp.startup_delay > 0:
                info(f"'{comp.name}' 안정화 대기 {comp.startup_delay:.0f}s...")
                time.sleep(comp.startup_delay)
            return True
        time.sleep(1.0)

    err(f"'{comp.name}' 준비 타임아웃 ({comp.startup_timeout:.0f}s)")
    return False


# ══════════════════════════════════════════════════════════════════
#  종료
# ══════════════════════════════════════════════════════════════════

def teardown(components: list[Component]) -> None:
    info("전체 정리 시작 (기동 역순)...")
    for comp in reversed(components):
        proc = comp.proc
        if not proc or proc.poll() is not None:
            continue
        info(f"'{comp.name}' 종료 신호...")
        try:
            proc.terminate() if IS_WIN else proc.send_signal(signal.SIGINT)
        except Exception:
            pass

    deadline = time.time() + 10
    for comp in reversed(components):
        if not comp.proc:
            continue
        try:
            comp.proc.wait(timeout=max(0.0, deadline - time.time()))
        except subprocess.TimeoutExpired:
            warn(f"'{comp.name}' 응답 없음 → 강제 종료(kill)")
            comp.proc.kill()
    info("정리 완료.")


# ══════════════════════════════════════════════════════════════════
#  메인
# ══════════════════════════════════════════════════════════════════

def parse_args():
    p = argparse.ArgumentParser(description="키오스크 통합테스트 런처")
    p.add_argument("--only", help="기동할 컴포넌트만 (예: ai,mcp)")
    p.add_argument("--skip", help="제외할 컴포넌트 (예: frontend)")
    p.add_argument("--no-color", action="store_true")
    return p.parse_args()


def main() -> int:
    global USE_COLOR
    args = parse_args()
    if args.no_color or not sys.stdout.isatty():
        USE_COLOR = False

    components = build_components()

    if args.only:
        keep = {s.strip() for s in args.only.split(",")}
        for c in components:
            c.enabled = c.name in keep
    if args.skip:
        drop = {s.strip() for s in args.skip.split(",")}
        for c in components:
            if c.name in drop:
                c.enabled = False

    active = [c for c in components if c.enabled]
    if not active:
        err("기동할 컴포넌트가 없습니다.")
        return 1

    info("통합테스트 런처 시작 — 대상: " + ", ".join(c.name for c in active))

    if any(c.name == "spring" for c in active):
        if _port_open(POSTGRES_PORT):
            info(f"PostgreSQL({POSTGRES_PORT}) OK")
        else:
            warn(f"PostgreSQL({POSTGRES_PORT}) 응답 없음 — pgAdmin/DB 확인 (Spring 기동 실패 가능)")

    started: list[Component] = []
    try:
        for idx, comp in enumerate(active):
            if not start_component(comp, idx + 1):
                teardown(started)
                return 1
            started.append(comp)
            if not wait_until_ready(comp):
                teardown(started)
                return 1

        info("✅ 전체 기동 완료. 통합테스트 진행 가능.")
        if any(c.name == "frontend" for c in active):
            info(f"   프론트:  http://localhost:{FRONTEND_PORT}")
        if any(c.name == "spring" for c in active):
            info(f"   Swagger: http://localhost:{SPRING_PORT}/swagger-ui/index.html")
        info("   종료: Ctrl+C")

        while True:
            time.sleep(1.0)
            for comp in started:
                if comp.proc and comp.proc.poll() is not None:
                    err(f"'{comp.name}' 비정상 종료 (exit={comp.proc.returncode}) → 전체 정리")
                    teardown(started)
                    return 1
    except KeyboardInterrupt:
        print()
        info("Ctrl+C — 종료 절차 시작")
        teardown(started)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
