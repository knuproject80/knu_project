package com.kiosk.entity;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "user_sessions")
public class UserSession {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "session_id", unique = true, nullable = false, length = 100)
    private String sessionId;

    @Column(name = "device_id", nullable = false, length = 100)
    private String deviceId;

    @Column(name = "detected_type", length = 50)
    private String detectedType;

    /** 현재 사용자가 보고 있는 페이지 (heartbeat 시 갱신) */
    @Column(name = "current_page", length = 200)
    private String currentPage;

    @Column(name = "started_at")
    private LocalDateTime startedAt;

    /** 마지막 활동 시각 — heartbeat·로그·모드변경 시 갱신 */
    @Column(name = "last_activity_at")
    private LocalDateTime lastActivityAt;

    @Column(name = "ended_at")
    private LocalDateTime endedAt;

    @Column(name = "duration_sec")
    private Integer durationSec;

    @Column(name = "is_completed")
    private Boolean isCompleted = false;

    /** 종료 사유: COMPLETED | CANCELLED | TIMEOUT | ERROR */
    @Column(name = "end_reason", length = 50)
    private String endReason;

    @PrePersist
    public void prePersist() {
        LocalDateTime now = LocalDateTime.now();
        this.startedAt = now;
        this.lastActivityAt = now;
    }

    // ── Getters ──

    public Long getId() { return id; }
    public String getSessionId() { return sessionId; }
    public String getDeviceId() { return deviceId; }
    public String getDetectedType() { return detectedType; }
    public String getCurrentPage() { return currentPage; }
    public LocalDateTime getStartedAt() { return startedAt; }
    public LocalDateTime getLastActivityAt() { return lastActivityAt; }
    public LocalDateTime getEndedAt() { return endedAt; }
    public Integer getDurationSec() { return durationSec; }
    public Boolean getIsCompleted() { return isCompleted; }
    public String getEndReason() { return endReason; }

    // ── Setters ──

    public void setDetectedType(String v) { this.detectedType = v; }
    public void setCurrentPage(String v) { this.currentPage = v; }
    public void setLastActivityAt(LocalDateTime v) { this.lastActivityAt = v; }
    public void setEndedAt(LocalDateTime v) { this.endedAt = v; }
    public void setDurationSec(Integer v) { this.durationSec = v; }
    public void setIsCompleted(Boolean v) { this.isCompleted = v; }
    public void setEndReason(String v) { this.endReason = v; }

    // ── Builder ──

    public static Builder builder() { return new Builder(); }

    public static class Builder {
        private final UserSession s = new UserSession();
        public Builder sessionId(String v) { s.sessionId = v; return this; }
        public Builder deviceId(String v) { s.deviceId = v; return this; }
        public Builder detectedType(String v) { s.detectedType = v; return this; }
        public Builder currentPage(String v) { s.currentPage = v; return this; }
        public UserSession build() { return s; }
    }
}
