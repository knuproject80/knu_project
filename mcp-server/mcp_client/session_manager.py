# session_manager.py
import asyncio
import time
import logging
from enum import Enum
from dataclasses import dataclass, field

import config

logger = logging.getLogger(__name__)


class SessionState(Enum):
    """세션 생명주기 상태"""
    WAITING   = "WAITING"      # 세션 생성됨, 서비스 진입 대기
    ACTIVE    = "ACTIVE"       # 서비스 이용 중
    COMPLETED = "COMPLETED"    # 정상 종료
    TIMEOUT   = "TIMEOUT"      # 시간 초과로 만료
    ERROR     = "ERROR"        # 오류로 중단


@dataclass
class Session:
    """
    변경 이력
    ─────────────────────────────────────────────────────────
    - conversation_history 필드 추가
      · AI /chat 호출 시 누적 대화 기록을 세션에 보관
      · main.py의 get_history / update_history 메서드에서 참조
    - prefilled 필드 추가 (v6.0)
      · AI /chat이 추출한 entities를 보관
      · STEP_CHANGE 수신 시 해당 단계가 이미 채워졌는지 판단하는 데 사용
      · main.py의 set_prefilled / is_step_prefilled / get_prefilled_value 메서드에서 참조
    ─────────────────────────────────────────────────────────
    """
    session_id:           str
    user_type:            str
    service_id:           int | None        = None
    state:                SessionState       = SessionState.WAITING
    created_at:           float              = field(default_factory=time.time)
    last_activity:        float              = field(default_factory=time.time)
    conversation_history: list               = field(default_factory=list)
    prefilled:            dict               = field(default_factory=dict)   # v6.0 추가

    def touch(self):
        """활동 시각 갱신"""
        self.last_activity = time.time()

    def is_expired(self) -> bool:
        return (time.time() - self.created_at) > config.SESSION_TIMEOUT_SEC

    def is_idle(self) -> bool:
        """세션 내 마지막 활동으로부터 타임아웃 초과 여부"""
        return (time.time() - self.last_activity) > config.SESSION_TIMEOUT_SEC


class SessionManager:
    """
    활성 세션을 추적하고 만료 세션을 자동 정리한다.

    변경 이력
    ─────────────────────────────────────────────────────────
    - create(): conversation_history 파라미터 추가
    - get_history(): 세션 대화 기록 조회 메서드 추가
    - update_history(): 세션 대화 기록 갱신 메서드 추가
    - set_prefilled(): AI entities를 세션에 저장 (v6.0)
    - is_step_prefilled(): 특정 step이 이미 채워졌는지 확인 (v6.0)
    - get_prefilled_value(): 특정 step의 prefilled 값 반환 (v6.0)
    - clear_prefilled_field(): 특정 step의 prefilled 값 초기화 (v6.0)
    ─────────────────────────────────────────────────────────
    """

    # step 키 → entities 필드 매핑 (v6.0)
    # STEP_CHANGE 수신 시 어느 entities 필드와 대응되는지 결정한다.
    _STEP_TO_ENTITY: dict[str, str] = {
        "CERTIFICATE_SELECT_COUNT":   "count",
        "CERTIFICATE_SELECT_SCOPE":   "scope",
    }

    def __init__(self):
        self._sessions: dict[str, Session] = {}
        self._cleanup_task: asyncio.Task | None = None

    # ── 생명주기 ────────────────────────────────

    def start(self):
        """백그라운드 정리 루프 시작 (이벤트 루프 내에서 호출)"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("세션 매니저 시작 — 정리 주기: %ds", config.SESSION_CLEANUP_INTERVAL)

    async def stop(self):
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
        logger.info("세션 매니저 종료")

    # ── 세션 CRUD ───────────────────────────────

    def create(
        self,
        session_id: str,
        user_type: str,
        conversation_history: list | None = None,  # 추가
    ) -> Session:
        """
        세션 생성.
        conversation_history를 초기값으로 받을 수 있다.
        VOICE_INPUT 시점에 AI /chat이 반환한 대화 기록을 여기서 저장한다.
        """
        session = Session(
            session_id=session_id,
            user_type=user_type,
            conversation_history=list(conversation_history or []),
        )
        self._sessions[session_id] = session
        logger.info("세션 생성: %s (유형: %s)", session_id, user_type)
        return session

    def get(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    def activate(self, session_id: str, service_id: int) -> Session | None:
        """세션을 ACTIVE 상태로 전환 + 서비스 ID 기록"""
        session = self._sessions.get(session_id)
        if session and session.state == SessionState.WAITING:
            session.state = SessionState.ACTIVE
            session.service_id = service_id
            session.touch()
            logger.info("세션 활성화: %s → 서비스 %d", session_id, service_id)
        return session

    def touch(self, session_id: str):
        """프론트 이벤트 수신 시 활동 시각 갱신"""
        session = self._sessions.get(session_id)
        if session:
            session.touch()

    def complete(self, session_id: str):
        """서비스 정상 완료"""
        session = self._sessions.get(session_id)
        if session:
            session.state = SessionState.COMPLETED
            logger.info("세션 완료: %s", session_id)

    def fail(self, session_id: str):
        """오류로 세션 중단"""
        session = self._sessions.get(session_id)
        if session:
            session.state = SessionState.ERROR
            logger.warning("세션 오류 중단: %s", session_id)

    def remove(self, session_id: str):
        removed = self._sessions.pop(session_id, None)
        if removed:
            logger.info("세션 제거: %s (상태: %s)", session_id, removed.state.value)

    # ── 대화 기록 관리 ───────────────────────────

    def get_history(self, session_id: str) -> list:
        """
        세션의 누적 대화 기록을 반환한다.
        main.py의 _handle_step_with_ai에서 AI /chat 호출 시 전달한다.
        세션이 없으면 빈 리스트를 반환한다.
        """
        session = self._sessions.get(session_id)
        if session is None:
            logger.debug("get_history: 세션 없음 — session_id=%s", session_id)
            return []
        return session.conversation_history

    def update_history(self, session_id: str, history: list) -> None:
        """
        AI /chat 응답의 conversation_history로 세션 기록을 갱신한다.
        main.py의 _handle_step_with_ai / _execute_service에서 호출한다.
        세션이 없거나 history가 list가 아니면 경고 후 무시한다.
        """
        if not isinstance(history, list):
            logger.warning(
                "update_history: list가 아닌 타입 무시 — session_id=%s type=%s",
                session_id, type(history).__name__,
            )
            return

        session = self._sessions.get(session_id)
        if session is None:
            logger.debug("update_history: 세션 없음 — session_id=%s", session_id)
            return

        session.conversation_history = history
        logger.debug(
            "대화 기록 갱신: session_id=%s 길이=%d",
            session_id, len(history),
        )

    # ── prefilled 관리 (v6.0) ────────────────────

    def set_prefilled(self, session_id: str, entities: dict) -> None:
        """
        AI /chat이 추출한 entities를 세션에 저장한다. (v6.0)

        VOICE_INPUT → AI /chat 응답 수신 직후 _handle_voice에서 호출한다.
        entities의 null 값은 저장하지 않아 is_step_prefilled가 False를 반환하도록 한다.

        Parameters
        ----------
        session_id : str
        entities : dict
            예: {"count": 1, "paymentMethod": "CASH", "purpose": None, "scope": None}
            null/None 값은 필터링하여 저장하지 않는다.
        """
        if not isinstance(entities, dict):
            logger.warning(
                "set_prefilled: dict가 아닌 타입 무시 — session_id=%s type=%s",
                session_id, type(entities).__name__,
            )
            return

        session = self._sessions.get(session_id)
        if session is None:
            logger.debug("set_prefilled: 세션 없음 — session_id=%s", session_id)
            return

        # None / 빈 문자열은 저장하지 않음 — is_step_prefilled가 False 반환하도록
        filtered = {k: v for k, v in entities.items() if v is not None and v != ""}
        session.prefilled = filtered
        logger.info(
            "prefilled 저장: session_id=%s fields=%s",
            session_id, list(filtered.keys()),
        )

    def is_step_prefilled(self, session_id: str, step: str) -> bool:
        """
        해당 step에 대응하는 entity가 이미 채워졌는지 확인한다. (v6.0)

        _STEP_TO_ENTITY 매핑에 없는 step은 항상 False를 반환한다.
        (전입신고 단계처럼 prefilled 대상이 아닌 step은 스킵하지 않는다.)

        Parameters
        ----------
        session_id : str
        step : str
            예: "CERTIFICATE_SELECT_COUNT"

        Returns
        -------
        bool
            True이면 main.py에서 AI 호출 없이 autoAdvance 처리한다.
        """
        entity_key = self._STEP_TO_ENTITY.get(step)
        if entity_key is None:
            return False  # 매핑 없는 step → 스킵 대상 아님

        session = self._sessions.get(session_id)
        if session is None:
            return False

        return entity_key in session.prefilled

    def get_prefilled_value(self, session_id: str, step: str):
        """
        해당 step의 prefilled 값을 반환한다. (v6.0)

        is_step_prefilled() 확인 후 호출하는 것을 권장한다.
        매핑이 없거나 세션이 없으면 None을 반환한다.

        Parameters
        ----------
        session_id : str
        step : str

        Returns
        -------
        Any | None
            저장된 값 (예: 1, "CASH") 또는 None
        """
        entity_key = self._STEP_TO_ENTITY.get(step)
        if entity_key is None:
            return None

        session = self._sessions.get(session_id)
        if session is None:
            return None

        return session.prefilled.get(entity_key)

    def clear_prefilled_field(self, session_id: str, step: str) -> None:
        """
        특정 step의 prefilled 값을 초기화한다. (v6.0)

        사용자가 자동입력된 값을 재발화로 수정하려 할 때 호출한다.
        예: "매수 변경해줘" → CERTIFICATE_SELECT_COUNT prefilled 초기화

        Parameters
        ----------
        session_id : str
        step : str
            초기화할 step 키
        """
        entity_key = self._STEP_TO_ENTITY.get(step)
        if entity_key is None:
            logger.debug(
                "clear_prefilled_field: 매핑 없는 step — session_id=%s step=%s",
                session_id, step,
            )
            return

        session = self._sessions.get(session_id)
        if session is None:
            return

        removed = session.prefilled.pop(entity_key, None)
        if removed is not None:
            logger.info(
                "prefilled 초기화: session_id=%s step=%s (이전 값: %s)",
                session_id, step, removed,
            )

    # ── 조회 ────────────────────────────────────

    @property
    def active_count(self) -> int:
        return sum(1 for s in self._sessions.values()
                   if s.state in (SessionState.WAITING, SessionState.ACTIVE))

    def get_active_session_ids(self) -> list[str]:
        return [sid for sid, s in self._sessions.items()
                if s.state in (SessionState.WAITING, SessionState.ACTIVE)]

    # ── 만료 콜백 (main에서 등록) ────────────────

    _on_timeout_callback = None

    def set_timeout_callback(self, callback):
        """callback(session: Session) — 만료 시 호출할 함수 등록"""
        self._on_timeout_callback = callback

    # ── 백그라운드 정리 ─────────────────────────

    async def _cleanup_loop(self):
        """주기적으로 만료 세션을 정리"""
        while True:
            await asyncio.sleep(config.SESSION_CLEANUP_INTERVAL)
            now = time.time()
            expired_ids = [
                sid for sid, s in self._sessions.items()
                if s.state in (SessionState.WAITING, SessionState.ACTIVE)
                and (now - s.last_activity) > config.SESSION_TIMEOUT_SEC
            ]
            for sid in expired_ids:
                session = self._sessions[sid]
                session.state = SessionState.TIMEOUT
                logger.warning(
                    "세션 타임아웃: %s (서비스: %s, 경과: %.0f초)",
                    sid, session.service_id,
                    now - session.created_at,
                )
                if self._on_timeout_callback:
                    try:
                        self._on_timeout_callback(session)
                    except Exception as e:
                        logger.error("타임아웃 콜백 오류: %s", e)

            # 종료 상태(COMPLETED, TIMEOUT, ERROR) 세션 최종 제거
            done_ids = [
                sid for sid, s in self._sessions.items()
                if s.state in (SessionState.COMPLETED, SessionState.TIMEOUT, SessionState.ERROR)
            ]
            for sid in done_ids:
                self._sessions.pop(sid, None)

            if expired_ids or done_ids:
                logger.info(
                    "세션 정리 완료 — 만료: %d, 제거: %d, 잔여 활성: %d",
                    len(expired_ids), len(done_ids), self.active_count,
                )
