package com.kiosk.service;

import com.kiosk.entity.UserSession;
import com.kiosk.repository.UserSessionRepository;
import com.kiosk.websocket.WebSocketNotifier;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.time.Duration;
import java.time.LocalDateTime;
import java.util.List;

/**
 * 주기적으로 유휴 세션을 탐지하고 자동 종료 처리한다.
 *
 * 기준: lastActivityAt 으로부터 sessionMaxTimeoutSec 초과 시 만료.
 * 만료된 세션에 대해:
 *  1) DB 상태를 TIMEOUT 으로 변경
 *  2) WebSocket 으로 SESSION_EXPIRED 를 프론트에 통지
 */
@Component
public class SessionCleanupScheduler {

    private static final Logger log = LoggerFactory.getLogger(SessionCleanupScheduler.class);

    private final UserSessionRepository sessionRepository;
    private final WebSocketNotifier webSocketNotifier;

    @Value("${kiosk.session.session-max-timeout-sec:300}")
    private int sessionMaxTimeoutSec;

    public SessionCleanupScheduler(UserSessionRepository sessionRepository,
                                    WebSocketNotifier webSocketNotifier) {
        this.sessionRepository = sessionRepository;
        this.webSocketNotifier = webSocketNotifier;
    }

    @Scheduled(fixedDelayString = "${kiosk.session.cleanup-interval-sec:30}000")
    @Transactional
    public void cleanupExpiredSessions() {
        LocalDateTime threshold = LocalDateTime.now().minusSeconds(sessionMaxTimeoutSec);
        List<UserSession> expired =
                sessionRepository.findByIsCompletedFalseAndLastActivityAtBefore(threshold);

        for (UserSession session : expired) {
            LocalDateTime now = LocalDateTime.now();
            long duration = Duration.between(session.getStartedAt(), now).getSeconds();

            session.setEndedAt(now);
            session.setDurationSec((int) duration);
            session.setIsCompleted(true);
            session.setEndReason("TIMEOUT");
            sessionRepository.save(session);

            // 프론트에 세션 만료 통지
            webSocketNotifier.sendSessionExpired(session.getSessionId(), "TIMEOUT");

            log.info("세션 자동 만료: sessionId={}, 경과={}초", session.getSessionId(), duration);
        }

        if (!expired.isEmpty()) {
            log.info("세션 정리 완료: {}건 만료 처리", expired.size());
        }
    }
}
