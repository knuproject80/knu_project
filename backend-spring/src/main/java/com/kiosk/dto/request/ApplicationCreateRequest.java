package com.kiosk.dto.request;

import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

public class ApplicationCreateRequest {

    @NotBlank(message = "sessionId는 필수입니다")
    private String sessionId;

    @NotNull(message = "serviceItemId는 필수입니다")
    private Long serviceItemId;

    @NotBlank(message = "applicantName은 필수입니다")
    private String applicantName;

    @Min(value = 1, message = "발급 부수는 1 이상이어야 합니다")
    private Integer copies = 1;

    private String purpose;
    private Integer feePaid = 0;

    public String getSessionId() { return sessionId; }
    public void setSessionId(String v) { this.sessionId = v; }
    public Long getServiceItemId() { return serviceItemId; }
    public void setServiceItemId(Long v) { this.serviceItemId = v; }
    public String getApplicantName() { return applicantName; }
    public void setApplicantName(String v) { this.applicantName = v; }
    public Integer getCopies() { return copies; }
    public void setCopies(Integer v) { this.copies = v; }
    public String getPurpose() { return purpose; }
    public void setPurpose(String v) { this.purpose = v; }
    public Integer getFeePaid() { return feePaid; }
    public void setFeePaid(Integer v) { this.feePaid = v; }
}
