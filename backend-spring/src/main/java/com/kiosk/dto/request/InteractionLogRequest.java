package com.kiosk.dto.request;

import jakarta.validation.constraints.NotBlank;

public class InteractionLogRequest {

    @NotBlank(message = "sessionId는 필수입니다")
    private String sessionId;

    @NotBlank(message = "actionType은 필수입니다")
    private String actionType;

    private String actionDetail;
    private String aiResponse;
    private Integer responseTime;

    public String getSessionId() { return sessionId; }
    public void setSessionId(String v) { this.sessionId = v; }
    public String getActionType() { return actionType; }
    public void setActionType(String v) { this.actionType = v; }
    public String getActionDetail() { return actionDetail; }
    public void setActionDetail(String v) { this.actionDetail = v; }
    public String getAiResponse() { return aiResponse; }
    public void setAiResponse(String v) { this.aiResponse = v; }
    public Integer getResponseTime() { return responseTime; }
    public void setResponseTime(Integer v) { this.responseTime = v; }
}
