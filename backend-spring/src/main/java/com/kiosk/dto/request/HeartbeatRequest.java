package com.kiosk.dto.request;

public class HeartbeatRequest {

    /** 현재 사용자가 보고 있는 페이지 식별자 (예: "certificate_purpose_select") */
    private String currentPage;

    public String getCurrentPage() { return currentPage; }
    public void setCurrentPage(String currentPage) { this.currentPage = currentPage; }
}
