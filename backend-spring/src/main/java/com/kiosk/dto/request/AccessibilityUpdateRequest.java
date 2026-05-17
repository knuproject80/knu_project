package com.kiosk.dto.request;

/**
 * PUT /api/session/{sessionId}/accessibility 요청 바디.
 *
 * - userType 을 보내면 해당 유형의 프리셋으로 전체 교체
 * - 개별 필드만 보내면 해당 필드만 부분 변경
 */
public class AccessibilityUpdateRequest {

    private String userType;
    private Boolean largeFont;
    private Boolean highContrast;
    private Boolean simpleMode;
    private Boolean voiceGuide;
    private Boolean lowScreenMode;
    private Integer fontSize;

    public String getUserType() { return userType; }
    public void setUserType(String v) { this.userType = v; }
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
