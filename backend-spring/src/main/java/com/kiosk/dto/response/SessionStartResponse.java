package com.kiosk.dto.response;

/**
 * POST /api/session/start 응답.
 *
 * pageIdleTimeoutSec / sessionMaxTimeoutSec 를 포함하여
 * 프론트가 페이지 단위 idle timer 를 설정할 수 있도록 한다.
 */
public class SessionStartResponse {

    private String sessionId;
    private String userType;
    private Boolean largeFont;
    private Boolean highContrast;
    private Boolean simpleMode;
    private Boolean voiceGuide;
    private Boolean lowScreenMode;
    private Integer fontSize;
    private Integer pageIdleTimeoutSec;
    private Integer sessionMaxTimeoutSec;

    public String getSessionId() { return sessionId; }
    public void setSessionId(String v) { this.sessionId = v; }
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
    public Integer getPageIdleTimeoutSec() { return pageIdleTimeoutSec; }
    public void setPageIdleTimeoutSec(Integer v) { this.pageIdleTimeoutSec = v; }
    public Integer getSessionMaxTimeoutSec() { return sessionMaxTimeoutSec; }
    public void setSessionMaxTimeoutSec(Integer v) { this.sessionMaxTimeoutSec = v; }
}
