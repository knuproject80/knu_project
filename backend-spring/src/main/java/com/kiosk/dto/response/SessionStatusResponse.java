package com.kiosk.dto.response;

import java.time.LocalDateTime;

/**
 * GET /api/session/{sessionId}/status 응답.
 *
 * 프론트가 새로고침 후에도 현재 세션의 모드·페이지 상태를
 * 복원할 수 있도록 전체 정보를 반환한다.
 */
public class SessionStatusResponse {

    private String sessionId;
    private String userType;
    private String currentPage;
    private Boolean isCompleted;
    private LocalDateTime startedAt;
    private LocalDateTime lastActivityAt;
    private Integer pageIdleTimeoutSec;
    private Integer sessionMaxTimeoutSec;
    private AccessibilitySettings accessibility;

    // ── 접근성 설정 내포 클래스 ──

    public static class AccessibilitySettings {
        private Boolean largeFont;
        private Boolean highContrast;
        private Boolean simpleMode;
        private Boolean voiceGuide;
        private Boolean lowScreenMode;
        private Integer fontSize;

        public Boolean getLargeFont() { return largeFont; }
        public void setLargeFont(Boolean v) { this.largeFont = v; }
        public Boolean getHighContrast() { return highContrast; }
        public void setHighContrast(Boolean v) { this.highContrast = v; }
        public Boolean getSimpleMode() { return simpleMode; }
        public void setSimpleMode(Boolean v) { this.simpleMode = v; }
        public Boolean getVoiceGuide() { return voiceGuide; }
        public void setVoiceGuide(Boolean v) { this.voiceGuide = v; }
        public Boolean getLowScreenMode() { return lowScreenMode; }
        public void setLowScreenMode(Boolean v) { this.lowScreenMode = v; }
        public Integer getFontSize() { return fontSize; }
        public void setFontSize(Integer v) { this.fontSize = v; }
    }

    // ── Getters / Setters ──

    public String getSessionId() { return sessionId; }
    public void setSessionId(String v) { this.sessionId = v; }
    public String getUserType() { return userType; }
    public void setUserType(String v) { this.userType = v; }
    public String getCurrentPage() { return currentPage; }
    public void setCurrentPage(String v) { this.currentPage = v; }
    public Boolean getIsCompleted() { return isCompleted; }
    public void setIsCompleted(Boolean v) { this.isCompleted = v; }
    public LocalDateTime getStartedAt() { return startedAt; }
    public void setStartedAt(LocalDateTime v) { this.startedAt = v; }
    public LocalDateTime getLastActivityAt() { return lastActivityAt; }
    public void setLastActivityAt(LocalDateTime v) { this.lastActivityAt = v; }
    public Integer getPageIdleTimeoutSec() { return pageIdleTimeoutSec; }
    public void setPageIdleTimeoutSec(Integer v) { this.pageIdleTimeoutSec = v; }
    public Integer getSessionMaxTimeoutSec() { return sessionMaxTimeoutSec; }
    public void setSessionMaxTimeoutSec(Integer v) { this.sessionMaxTimeoutSec = v; }
    public AccessibilitySettings getAccessibility() { return accessibility; }
    public void setAccessibility(AccessibilitySettings v) { this.accessibility = v; }
}
