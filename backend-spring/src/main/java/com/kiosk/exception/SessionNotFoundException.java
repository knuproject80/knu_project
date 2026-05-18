package com.kiosk.exception;

public class SessionNotFoundException extends RuntimeException {
    public SessionNotFoundException(String sessionId) {
        super("세션을 찾을 수 없습니다: " + sessionId);
    }
}
