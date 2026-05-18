package com.kiosk.dto.request;

import jakarta.validation.constraints.NotBlank;

public class SessionStartRequest {

    @NotBlank(message = "deviceId는 필수입니다")
    private String deviceId;

    private String detectedType = "NORMAL";

    public String getDeviceId() { return deviceId; }
    public void setDeviceId(String deviceId) { this.deviceId = deviceId; }
    public String getDetectedType() { return detectedType; }
    public void setDetectedType(String detectedType) { this.detectedType = detectedType; }
}
