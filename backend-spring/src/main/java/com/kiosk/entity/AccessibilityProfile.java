package com.kiosk.entity;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "accessibility_profiles")
public class AccessibilityProfile {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "device_id", nullable = false, length = 100)
    private String deviceId;

    @Column(name = "session_id", length = 100)
    private String sessionId;

    @Enumerated(EnumType.STRING)
    @Column(name = "user_type", nullable = false, length = 50)
    private UserType userType;

    @Column(name = "large_font")
    private Boolean largeFont = false;

    @Column(name = "high_contrast")
    private Boolean highContrast = false;

    @Column(name = "simple_mode")
    private Boolean simpleMode = false;

    @Column(name = "voice_guide")
    private Boolean voiceGuide = false;

    @Column(name = "low_screen_mode")
    private Boolean lowScreenMode = false;

    @Column(name = "font_size")
    private Integer fontSize = 16;

    @Column(name = "created_at")
    private LocalDateTime createdAt;

    @Column(name = "updated_at")
    private LocalDateTime updatedAt;

    @PrePersist
    public void prePersist() {
        this.createdAt = LocalDateTime.now();
        this.updatedAt = LocalDateTime.now();
    }

    @PreUpdate
    public void preUpdate() {
        this.updatedAt = LocalDateTime.now();
    }

    public enum UserType {
        ELDERLY,              // 고령자  → 확대 + 고대비 + 단순모드 + 음성
        WHEELCHAIR,           // 휠체어  → 낮은 화면 모드
        VISUALLY_IMPAIRED,    // 시각장애 → 최대 확대 + 음성 안내
        HEARING_IMPAIRED,     // 청각장애 → 고대비 + 자막 강화
        NORMAL                // 일반
    }

    // ── Getters ──

    public Long getId() { return id; }
    public String getDeviceId() { return deviceId; }
    public String getSessionId() { return sessionId; }
    public UserType getUserType() { return userType; }
    public Boolean getLargeFont() { return largeFont; }
    public Boolean getHighContrast() { return highContrast; }
    public Boolean getSimpleMode() { return simpleMode; }
    public Boolean getVoiceGuide() { return voiceGuide; }
    public Boolean getLowScreenMode() { return lowScreenMode; }
    public Integer getFontSize() { return fontSize; }
    public LocalDateTime getCreatedAt() { return createdAt; }
    public LocalDateTime getUpdatedAt() { return updatedAt; }

    // ── Setters ──

    public void setDeviceId(String v) { this.deviceId = v; }
    public void setSessionId(String v) { this.sessionId = v; }
    public void setUserType(UserType v) { this.userType = v; }
    public void setLargeFont(Boolean v) { this.largeFont = v; }
    public void setHighContrast(Boolean v) { this.highContrast = v; }
    public void setSimpleMode(Boolean v) { this.simpleMode = v; }
    public void setVoiceGuide(Boolean v) { this.voiceGuide = v; }
    public void setLowScreenMode(Boolean v) { this.lowScreenMode = v; }
    public void setFontSize(Integer v) { this.fontSize = v; }

    // ── Builder ──

    public static Builder builder() { return new Builder(); }

    public static class Builder {
        private final AccessibilityProfile p = new AccessibilityProfile();
        public Builder sessionId(String v) { p.sessionId = v; return this; }
        public Builder deviceId(String v) { p.deviceId = v; return this; }
        public Builder userType(UserType v) { p.userType = v; return this; }
        public Builder largeFont(Boolean v) { p.largeFont = v; return this; }
        public Builder highContrast(Boolean v) { p.highContrast = v; return this; }
        public Builder simpleMode(Boolean v) { p.simpleMode = v; return this; }
        public Builder voiceGuide(Boolean v) { p.voiceGuide = v; return this; }
        public Builder lowScreenMode(Boolean v) { p.lowScreenMode = v; return this; }
        public Builder fontSize(Integer v) { p.fontSize = v; return this; }
        public AccessibilityProfile build() { return p; }
    }
}
