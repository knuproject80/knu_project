package com.kiosk.service;

import com.kiosk.dto.response.SessionStartResponse;
import com.kiosk.dto.response.SessionStatusResponse;
import com.kiosk.entity.AccessibilityProfile;
import com.kiosk.entity.AccessibilityProfile.UserType;
import com.kiosk.entity.InteractionLog;
import com.kiosk.entity.UserSession;
import com.kiosk.exception.SessionNotFoundException;
import com.kiosk.repository.AccessibilityProfileRepository;
import com.kiosk.repository.InteractionLogRepository;
import com.kiosk.repository.UserSessionRepository;
import com.kiosk.websocket.WebSocketNotifier;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Duration;
import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

@Service
public class SessionService {

    private static final Logger log = LoggerFactory.getLogger(SessionService.class);

    private final UserSessionRepository sessionRepository;
    private final AccessibilityProfileRepository profileRepository;
    private final InteractionLogRepository logRepository;
    private final WebSocketNotifier webSocketNotifier;

    @Value("${kiosk.session.page-idle-timeout-sec:60}")
    private int pageIdleTimeoutSec;

    @Value("${kiosk.session.session-max-timeout-sec:300}")
    private int sessionMaxTimeoutSec;

    public SessionService(UserSessionRepository sessionRepository,
                          AccessibilityProfileRepository profileRepository,
                          InteractionLogRepository logRepository,
                          WebSocketNotifier webSocketNotifier) {
        this.sessionRepository = sessionRepository;
        this.profileRepository = profileRepository;
        this.logRepository = logRepository;
        this.webSocketNotifier = webSocketNotifier;
    }

    // ══════════════════════════════════════════════
    //  세션 시작
    //
    //  응답에 pageIdleTimeoutSec, sessionMaxTimeoutSec 을 포함하여
    //  프론트가 페이지 단위 idle timer 를 설정할 수 있도록 한다.
    // ══════════════════════════════════════════════

    @Transactional
    public SessionStartResponse startSession(String deviceId, String detectedType) {
        String sessionId = UUID.randomUUID().toString();

        UserSession session = UserSession.builder()
                .sessionId(sessionId)
                .deviceId(deviceId)
                .detectedType(detectedType)
                .build();
        sessionRepository.save(session);

        UserType userType = parseUserType(detectedType);
        AccessibilityProfile profile = buildProfileByUserType(sessionId, deviceId, userType);
        profileRepository.save(profile);

        log.info("세션 시작: sessionId={}, deviceId={}, userType={}", sessionId, deviceId, userType);

        SessionStartResponse response = new SessionStartResponse();
        response.setSessionId(sessionId);
        response.setUserType(userType.name());
        response.setLargeFont(profile.getLargeFont());
        response.setHighContrast(profile.getHighContrast());
        response.setSimpleMode(profile.getSimpleMode());
        response.setVoiceGuide(profile.getVoiceGuide());
        response.setLowScreenMode(profile.getLowScreenMode());
        response.setFontSize(profile.getFontSize());
        response.setPageIdleTimeoutSec(pageIdleTimeoutSec);
        response.setSessionMaxTimeoutSec(sessionMaxTimeoutSec);
        return response;
    }

    // ══════════════════════════════════════════════
    //  세션 종료
    //
    //  reason 을 기록하여 종료 원인 추적 가능.
    //  이미 종료된 세션에 대한 중복 호출은 무시.
    // ══════════════════════════════════════════════

    @Transactional
    public void endSession(String sessionId, String reason) {
        UserSession session = findSessionOrThrow(sessionId);

        if (session.getIsCompleted()) {
            log.warn("이미 종료된 세션 — 무시: sessionId={}", sessionId);
            return;
        }

        LocalDateTime now = LocalDateTime.now();
        long duration = Duration.between(session.getStartedAt(), now).getSeconds();
        session.setEndedAt(now);
        session.setDurationSec((int) duration);
        session.setIsCompleted(true);
        session.setEndReason(reason != null ? reason : "COMPLETED");
        sessionRepository.save(session);

        log.info("세션 종료: sessionId={}, reason={}, duration={}초", sessionId, reason, duration);
    }

    // ══════════════════════════════════════════════
    //  heartbeat — 페이지별 활동 갱신
    //
    //  프론트가 페이지 전환 또는 사용자 조작 시 호출.
    //  호출할 때마다 lastActivityAt 이 갱신되므로
    //  프론트에서 페이지 단위 idle timer 를 구현할 수 있다.
    //
    //  응답에 sessionRemainingSeconds 를 포함하여
    //  전체 세션 만료까지 남은 시간도 알 수 있다.
    // ══════════════════════════════════════════════

    @Transactional
    public Map<String, Object> heartbeat(String sessionId, String currentPage) {
        UserSession session = findSessionOrThrow(sessionId);

        if (session.getIsCompleted()) {
            throw new IllegalArgumentException("이미 종료된 세션입니다: " + sessionId);
        }

        LocalDateTime now = LocalDateTime.now();

        // 전체 세션 타임아웃 초과 체크
        long sessionElapsed = Duration.between(session.getStartedAt(), now).getSeconds();
        if (sessionElapsed > sessionMaxTimeoutSec) {
            endSession(sessionId, "TIMEOUT");
            webSocketNotifier.sendSessionExpired(sessionId, "TIMEOUT");
            throw new IllegalArgumentException("세션이 만료되었습니다 (전체 타임아웃 초과)");
        }

        // 활동 시각 + 현재 페이지 갱신
        session.setLastActivityAt(now);
        if (currentPage != null && !currentPage.isBlank()) {
            session.setCurrentPage(currentPage);
        }
        sessionRepository.save(session);

        Map<String, Object> result = new HashMap<>();
        result.put("sessionId", sessionId);
        result.put("lastActivityAt", now.toString());
        result.put("currentPage", session.getCurrentPage());
        result.put("pageIdleTimeoutSec", pageIdleTimeoutSec);
        result.put("sessionRemainingSeconds",
                Math.max(0, sessionMaxTimeoutSec - (int) sessionElapsed));
        return result;
    }

    // ══════════════════════════════════════════════
    //  접근성 설정 변경 + WebSocket 즉시 통지
    //
    //  [핵심 개선] 기존에는 DB 만 업데이트하고 끝이었으나,
    //  이제 DB 업데이트 후 WebSocket 으로 프론트에 즉시 통지한다.
    //  → 팀원 이슈 #3 (모드 적용 로직과 상태값 분리) 해결
    //
    //  userType 을 보내면 해당 유형의 프리셋으로 전체 교체.
    //  개별 필드만 보내면 부분 업데이트.
    // ══════════════════════════════════════════════

    @Transactional
    public Map<String, Object> updateAccessibility(String sessionId, String userTypeStr,
                                                    Boolean largeFont, Boolean highContrast,
                                                    Boolean simpleMode, Boolean voiceGuide,
                                                    Boolean lowScreenMode, Integer fontSize) {

        AccessibilityProfile profile = profileRepository.findBySessionId(sessionId)
                .orElseThrow(() -> new SessionNotFoundException(sessionId));

        if (userTypeStr != null && !userTypeStr.isBlank()) {
            // userType 프리셋 전체 교체
            UserType newType = parseUserType(userTypeStr);
            applyPreset(profile, newType);
        } else {
            // 개별 필드만 부분 변경
            if (largeFont != null) profile.setLargeFont(largeFont);
            if (highContrast != null) profile.setHighContrast(highContrast);
            if (simpleMode != null) profile.setSimpleMode(simpleMode);
            if (voiceGuide != null) profile.setVoiceGuide(voiceGuide);
            if (lowScreenMode != null) profile.setLowScreenMode(lowScreenMode);
            if (fontSize != null) profile.setFontSize(fontSize);
        }
        profileRepository.save(profile);

        // 활동 시각 갱신 (모드 변경도 활동)
        sessionRepository.findBySessionId(sessionId).ifPresent(session -> {
            session.setLastActivityAt(LocalDateTime.now());
            sessionRepository.save(session);
        });

        // WebSocket 으로 프론트에 즉시 통지
        Map<String, Object> uiSettings = buildUiSettingsMap(profile);
        webSocketNotifier.sendUiUpdate(sessionId, uiSettings);

        log.info("접근성 설정 변경 + WS 통지: sessionId={}, userType={}", sessionId, profile.getUserType());
        return uiSettings;
    }

    // ══════════════════════════════════════════════
    //  세션 상태 조회
    //
    //  프론트가 새로고침 후에도 현재 세션의 모드·페이지 상태를
    //  복원할 수 있도록 전체 정보를 반환한다.
    //  → 팀원 이슈 #4 (새로고침 후 모드 적용 불가) 해결
    // ══════════════════════════════════════════════

    @Transactional(readOnly = true)
    public SessionStatusResponse getSessionStatus(String sessionId) {
        UserSession session = findSessionOrThrow(sessionId);

        SessionStatusResponse resp = new SessionStatusResponse();
        resp.setSessionId(session.getSessionId());
        resp.setUserType(session.getDetectedType());
        resp.setCurrentPage(session.getCurrentPage());
        resp.setIsCompleted(session.getIsCompleted());
        resp.setStartedAt(session.getStartedAt());
        resp.setLastActivityAt(session.getLastActivityAt());
        resp.setPageIdleTimeoutSec(pageIdleTimeoutSec);
        resp.setSessionMaxTimeoutSec(sessionMaxTimeoutSec);

        // 접근성 프로필 정보 포함
        profileRepository.findBySessionId(sessionId).ifPresent(profile -> {
            SessionStatusResponse.AccessibilitySettings a =
                    new SessionStatusResponse.AccessibilitySettings();
            a.setLargeFont(profile.getLargeFont());
            a.setHighContrast(profile.getHighContrast());
            a.setSimpleMode(profile.getSimpleMode());
            a.setVoiceGuide(profile.getVoiceGuide());
            a.setLowScreenMode(profile.getLowScreenMode());
            a.setFontSize(profile.getFontSize());
            resp.setAccessibility(a);
            resp.setUserType(profile.getUserType().name());
        });

        return resp;
    }

    // ══════════════════════════════════════════════
    //  행동 로그 저장
    // ══════════════════════════════════════════════

    @Transactional
    public void saveLog(String sessionId, String actionType, String actionDetail,
                        String aiResponse, Integer responseTime) {

        if (sessionRepository.findBySessionId(sessionId).isEmpty()) {
            throw new SessionNotFoundException(sessionId);
        }

        InteractionLog interactionLog = InteractionLog.builder()
                .sessionId(sessionId)
                .actionType(actionType)
                .actionDetail(actionDetail)
                .aiResponse(aiResponse)
                .responseTime(responseTime)
                .build();
        logRepository.save(interactionLog);

        // 로그 저장도 활동으로 간주 → lastActivityAt 갱신
        sessionRepository.findBySessionId(sessionId).ifPresent(session -> {
            session.setLastActivityAt(LocalDateTime.now());
            sessionRepository.save(session);
        });
    }

    // ══════════════════════════════════════════════
    //  내부 헬퍼
    // ══════════════════════════════════════════════

    private UserSession findSessionOrThrow(String sessionId) {
        return sessionRepository.findBySessionId(sessionId)
                .orElseThrow(() -> new SessionNotFoundException(sessionId));
    }

    private UserType parseUserType(String detectedType) {
        if (detectedType == null || detectedType.isBlank()) return UserType.NORMAL;
        try {
            return UserType.valueOf(detectedType.toUpperCase());
        } catch (IllegalArgumentException e) {
            log.warn("알 수 없는 사용자 유형 '{}' → NORMAL 대체", detectedType);
            return UserType.NORMAL;
        }
    }

    /** userType 프리셋을 profile 에 일괄 적용 */
    private void applyPreset(AccessibilityProfile profile, UserType userType) {
        profile.setUserType(userType);
        switch (userType) {
            case ELDERLY -> {
                profile.setLargeFont(true);
                profile.setHighContrast(true);
                profile.setSimpleMode(true);
                profile.setVoiceGuide(true);
                profile.setLowScreenMode(false);
                profile.setFontSize(24);
            }
            case WHEELCHAIR -> {
                profile.setLargeFont(false);
                profile.setHighContrast(false);
                profile.setSimpleMode(false);
                profile.setVoiceGuide(false);
                profile.setLowScreenMode(true);
                profile.setFontSize(20);
            }
            case VISUALLY_IMPAIRED -> {
                profile.setLargeFont(true);
                profile.setHighContrast(true);
                profile.setSimpleMode(true);
                profile.setVoiceGuide(true);
                profile.setLowScreenMode(false);
                profile.setFontSize(28);
            }
            case HEARING_IMPAIRED -> {
                profile.setLargeFont(false);
                profile.setHighContrast(true);
                profile.setSimpleMode(false);
                profile.setVoiceGuide(false);
                profile.setLowScreenMode(false);
                profile.setFontSize(18);
            }
            default -> {
                profile.setLargeFont(false);
                profile.setHighContrast(false);
                profile.setSimpleMode(false);
                profile.setVoiceGuide(false);
                profile.setLowScreenMode(false);
                profile.setFontSize(16);
            }
        }
    }

    private AccessibilityProfile buildProfileByUserType(
            String sessionId, String deviceId, UserType userType) {

        AccessibilityProfile.Builder b = AccessibilityProfile.builder()
                .sessionId(sessionId)
                .deviceId(deviceId)
                .userType(userType);

        return switch (userType) {
            case ELDERLY ->
                b.largeFont(true).highContrast(true)
                    .simpleMode(true).voiceGuide(true).fontSize(24).build();
            case WHEELCHAIR ->
                b.lowScreenMode(true).fontSize(20).build();
            case VISUALLY_IMPAIRED ->
                b.largeFont(true).highContrast(true)
                    .simpleMode(true).voiceGuide(true).fontSize(28).build();
            case HEARING_IMPAIRED ->
                b.highContrast(true).fontSize(18).build();
            default ->
                b.fontSize(16).build();
        };
    }

    private Map<String, Object> buildUiSettingsMap(AccessibilityProfile profile) {
        Map<String, Object> m = new HashMap<>();
        m.put("userType", profile.getUserType().name());
        m.put("largeFont", profile.getLargeFont());
        m.put("highContrast", profile.getHighContrast());
        m.put("simpleMode", profile.getSimpleMode());
        m.put("voiceGuide", profile.getVoiceGuide());
        m.put("lowScreenMode", profile.getLowScreenMode());
        m.put("fontSize", profile.getFontSize());
        return m;
    }
}
