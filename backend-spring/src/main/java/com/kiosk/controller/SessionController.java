package com.kiosk.controller;

import com.kiosk.dto.request.*;
import com.kiosk.dto.response.ApiResponse;
import com.kiosk.dto.response.SessionStartResponse;
import com.kiosk.dto.response.SessionStatusResponse;
import com.kiosk.service.SessionService;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/session")
public class SessionController {

    private final SessionService sessionService;

    public SessionController(SessionService sessionService) {
        this.sessionService = sessionService;
    }

    // -------------------------------------------------------
    // POST /api/session/start
    // 사용자 감지 시 세션 시작
    //
    // 요청: { "deviceId": "kiosk-001", "detectedType": "ELDERLY" }
    // detectedType: ELDERLY, WHEELCHAIR, VISUALLY_IMPAIRED,
    //               HEARING_IMPAIRED, NORMAL
    //
    // 응답에 pageIdleTimeoutSec, sessionMaxTimeoutSec 포함
    // → 프론트가 이 값으로 페이지 단위 idle timer 설정
    // -------------------------------------------------------
    @PostMapping("/start")
    public ResponseEntity<ApiResponse<SessionStartResponse>> startSession(
            @Valid @RequestBody SessionStartRequest request) {

        SessionStartResponse result = sessionService.startSession(
                request.getDeviceId(),
                request.getDetectedType()
        );
        return ResponseEntity.ok(ApiResponse.ok("세션이 시작되었습니다", result));
    }

    // -------------------------------------------------------
    // POST /api/session/end
    // 세션 종료 (사용자 이탈 / 완료 / 취소 / 타임아웃)
    //
    // 요청: { "sessionId": "abc-123", "reason": "COMPLETED" }
    // reason: COMPLETED | CANCELLED | TIMEOUT | ERROR
    // -------------------------------------------------------
    @PostMapping("/end")
    public ResponseEntity<ApiResponse<Void>> endSession(
            @Valid @RequestBody SessionEndRequest request) {

        sessionService.endSession(request.getSessionId(), request.getReason());
        return ResponseEntity.ok(ApiResponse.ok("세션이 종료되었습니다"));
    }

    // -------------------------------------------------------
    // POST /api/session/{sessionId}/heartbeat
    // 페이지별 활동 갱신
    //
    // 프론트가 주기적으로 또는 사용자 조작/페이지 전환 시 호출.
    // 호출마다 lastActivityAt 갱신 → idle timer 리셋.
    //
    // 요청: { "currentPage": "certificate_purpose_select" }
    //
    // 응답: pageIdleTimeoutSec, sessionRemainingSeconds 포함
    // -------------------------------------------------------
    @PostMapping("/{sessionId}/heartbeat")
    public ResponseEntity<ApiResponse<Map<String, Object>>> heartbeat(
            @PathVariable String sessionId,
            @RequestBody(required = false) HeartbeatRequest request) {

        String currentPage = (request != null) ? request.getCurrentPage() : null;
        Map<String, Object> result = sessionService.heartbeat(sessionId, currentPage);
        return ResponseEntity.ok(ApiResponse.ok(result));
    }

    // -------------------------------------------------------
    // GET /api/session/{sessionId}/status
    // 세션 상태 조회 — 새로고침 후 상태 복원용
    //
    // 응답: 현재 userType, accessibility 설정, currentPage,
    //       pageIdleTimeoutSec, sessionMaxTimeoutSec
    // -------------------------------------------------------
    @GetMapping("/{sessionId}/status")
    public ResponseEntity<ApiResponse<SessionStatusResponse>> getSessionStatus(
            @PathVariable String sessionId) {

        SessionStatusResponse result = sessionService.getSessionStatus(sessionId);
        return ResponseEntity.ok(ApiResponse.ok(result));
    }

    // -------------------------------------------------------
    // PUT /api/session/{sessionId}/accessibility
    // 접근성 설정 변경
    //
    // userType 을 보내면 → 해당 유형의 프리셋 일괄 적용
    // 개별 필드만 보내면 → 부분 변경
    //
    // 변경 즉시 WebSocket /topic/ui/{sessionId} 로 ADAPT_UI 통지
    //
    // 요청: { "userType": "ELDERLY" }
    // 또는: { "largeFont": true, "fontSize": 24 }
    // -------------------------------------------------------
    @PutMapping("/{sessionId}/accessibility")
    public ResponseEntity<ApiResponse<Map<String, Object>>> updateAccessibility(
            @PathVariable String sessionId,
            @RequestBody AccessibilityUpdateRequest request) {

        Map<String, Object> result = sessionService.updateAccessibility(
                sessionId,
                request.getUserType(),
                request.getLargeFont(),
                request.getHighContrast(),
                request.getSimpleMode(),
                request.getVoiceGuide(),
                request.getLowScreenMode(),
                request.getFontSize()
        );
        return ResponseEntity.ok(ApiResponse.ok("UI 설정이 변경되었습니다", result));
    }

    // -------------------------------------------------------
    // POST /api/session/log
    // 행동 기록 (버튼 클릭, 음성 입력, AI 응답 등)
    //
    // 요청:
    // {
    //   "sessionId": "abc-123",
    //   "actionType": "BUTTON_CLICK",
    //   "actionDetail": "주민등록등본 선택"
    // }
    // -------------------------------------------------------
    @PostMapping("/log")
    public ResponseEntity<ApiResponse<Void>> saveLog(
            @Valid @RequestBody InteractionLogRequest request) {

        sessionService.saveLog(
                request.getSessionId(),
                request.getActionType(),
                request.getActionDetail(),
                request.getAiResponse(),
                request.getResponseTime()
        );
        return ResponseEntity.ok(ApiResponse.ok("로그가 저장되었습니다"));
    }
}
