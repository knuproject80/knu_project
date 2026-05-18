package com.kiosk.websocket;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

/**
 * STOMP 메시지 발행 컴포넌트.
 *
 * 모든 메시지는 wrapCommand()로 감싸져 commandId + timestamp 를 포함하며,
 * 프론트가 ACK 추적이나 중복 수신 방지에 활용할 수 있다.
 */
@Component
public class WebSocketNotifier {

    private static final Logger log = LoggerFactory.getLogger(WebSocketNotifier.class);

    private final SimpMessagingTemplate messagingTemplate;

    public WebSocketNotifier(SimpMessagingTemplate messagingTemplate) {
        this.messagingTemplate = messagingTemplate;
    }

    // ══════════════════════════════════════════════
    //  UI 설정 변경 통지 (ADAPT_UI)
    // ══════════════════════════════════════════════

    /** 세션별 통지 → /topic/ui/{sessionId} */
    public void sendUiUpdate(String sessionId, Map<String, Object> uiSettings) {
        Map<String, Object> msg = wrapCommand("ADAPT_UI", uiSettings);
        messagingTemplate.convertAndSend("/topic/ui/" + sessionId, msg);
        log.info("UI 설정 변경 통지: sessionId={}, userType={}", sessionId, uiSettings.get("userType"));
    }

    /** 글로벌 통지 (세션 무관) → /topic/ui/global */
    public void sendGlobalUiUpdate(Map<String, Object> uiSettings) {
        Map<String, Object> msg = wrapCommand("ADAPT_UI", uiSettings);
        messagingTemplate.convertAndSend("/topic/ui/global", msg);
        log.info("글로벌 UI 변경 통지: userType={}", uiSettings.get("userType"));
    }

    // ══════════════════════════════════════════════
    //  세션 만료 통지 (SESSION_EXPIRED)
    // ══════════════════════════════════════════════

    public void sendSessionExpired(String sessionId, String reason) {
        Map<String, Object> data = new HashMap<>();
        data.put("reason", reason);
        data.put("message", "시간이 초과되었습니다. 처음 화면으로 돌아갑니다.");
        Map<String, Object> msg = wrapCommand("SESSION_EXPIRED", data);
        messagingTemplate.convertAndSend("/topic/ui/" + sessionId, msg);
        log.info("세션 만료 통지: sessionId={}, reason={}", sessionId, reason);
    }

    // ══════════════════════════════════════════════
    //  AI 응답 전달 (AI_RESPONSE)
    // ══════════════════════════════════════════════

    public void sendAiResponse(String sessionId, String responseText) {
        Map<String, Object> data = new HashMap<>();
        data.put("text", responseText);
        Map<String, Object> msg = wrapCommand("AI_RESPONSE", data);
        messagingTemplate.convertAndSend("/topic/ai/" + sessionId, msg);
    }

    // ══════════════════════════════════════════════
    //  음성 안내 (VOICE_GUIDE)
    // ══════════════════════════════════════════════

    public void sendVoiceGuide(String sessionId, String guideText, String context) {
        Map<String, Object> data = new HashMap<>();
        data.put("guideText", guideText);
        data.put("context", context);

        String dest = (sessionId != null && !"global".equals(sessionId))
                ? "/topic/ui/" + sessionId
                : "/topic/ui/global";

        messagingTemplate.convertAndSend(dest, wrapCommand("VOICE_GUIDE", data));
    }

    // ══════════════════════════════════════════════
    //  페이지 이동 (MOVE_PAGE)
    // ══════════════════════════════════════════════

    public void sendMovePage(String sessionId, Map<String, Object> pageData) {
        messagingTemplate.convertAndSend(
                "/topic/ui/" + sessionId, wrapCommand("MOVE_PAGE", pageData));
        log.info("페이지 이동 통지: sessionId={}, serviceId={}", sessionId, pageData.get("serviceId"));
    }

    // ══════════════════════════════════════════════
    //  홈 화면 복귀 (GO_HOME)
    // ══════════════════════════════════════════════

    public void sendGoHome(String sessionId) {
        Map<String, Object> data = new HashMap<>();
        data.put("message", "처음 화면으로 돌아갑니다.");

        String dest = (sessionId != null)
                ? "/topic/ui/" + sessionId
                : "/topic/ui/global";

        messagingTemplate.convertAndSend(dest, wrapCommand("GO_HOME", data));
        log.info("홈 복귀 통지: sessionId={}", sessionId);
    }

    // ══════════════════════════════════════════════
    //  내부 헬퍼
    // ══════════════════════════════════════════════

    private Map<String, Object> wrapCommand(String action, Map<String, Object> data) {
        Map<String, Object> message = new HashMap<>();
        message.put("action", action);
        message.put("commandId", UUID.randomUUID().toString());
        message.put("timestamp", LocalDateTime.now().toString());
        message.put("data", data);
        return message;
    }
}
