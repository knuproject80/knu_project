package com.kiosk.dto.request;

import jakarta.validation.constraints.NotBlank;

public class SessionEndRequest {

    @NotBlank(message = "sessionId는 필수입니다")
    private String sessionId;

    /** COMPLETED | CANCELLED | TIMEOUT | ERROR */
    private String reason = "COMPLETED";

    public String getSessionId() { return sessionId; }
    public void setSessionId(String sessionId) { this.sessionId = sessionId; }
    public String getReason() { return reason; }
    public void setReason(String reason) { this.reason = reason; }
}
