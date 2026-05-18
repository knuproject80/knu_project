package com.kiosk.repository;

import com.kiosk.entity.UserSession;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

@Repository
public interface UserSessionRepository extends JpaRepository<UserSession, Long> {

    Optional<UserSession> findBySessionId(String sessionId);

    List<UserSession> findByDeviceIdOrderByStartedAtDesc(String deviceId);

    List<UserSession> findByDeviceIdAndIsCompletedFalse(String deviceId);

    /** 만료 세션 자동 정리용 — lastActivityAt 이 threshold 이전이고 미종료인 세션 */
    List<UserSession> findByIsCompletedFalseAndLastActivityAtBefore(LocalDateTime threshold);
}
