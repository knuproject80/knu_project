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
 * 모든 메시지는 wrapCommand()로 감싸져 action + commandId + timestamp + data 형식을 갖춘다.
 * 프론트/MCP Client 가 commandId로 ACK 추적이나 중복 수신 방지에 활용할 수 있다.
 *
 * 토픽 구조 (MCP Client 테스트 가이드 문서 4.2 절 기준):
 *  - /topic/ui/{sessionId} : 세션별 명령 전송
 *  - /topic/ui/global      : 글로벌 명령 전송 (세션 미지정)
 *  - /topic/ai/{sessionId} : AI 응답 전송
 *  - /topic/front/events   : 프론트 이벤트 (StompRelayController가 중계)
 *  - /topic/front/ack      : ACK 응답 (StompRelayController가 중계)
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
    //
    //  Payload (문서 4.3절):
    //  {
    //    "action": "ADAPT_UI",
    //    "commandId": "uuid",
    //    "data": {
    //      "userType": "ELDERLY",
    //      "settings": {
    //        "largeFont": true, "highContrast": true,
    //        "simpleMode": true, "fontSize": "24px"
    //      }
    //    }
    //  }
    // ══════════════════════════════════════════════

    /** 세션별 통지 → /topic/ui/{sessionId} */
    public void sendUiUpdate(String sessionId, Map<String, Object> uiSettings) {
        Map<String, Object> data = buildAdaptUiData(uiSettings);
        Map<String, Object> msg = wrapCommand("ADAPT_UI", data);
        messagingTemplate.convertAndSend("/topic/ui/" + sessionId, msg);
        log.info("UI 설정 변경 통지: sessionId={}, userType={}", sessionId, uiSettings.get("userType"));
    }

    /** 글로벌 통지 (세션 무관) → /topic/ui/global */
    public void sendGlobalUiUpdate(Map<String, Object> uiSettings) {
        Map<String, Object> data = buildAdaptUiData(uiSettings);
        Map<String, Object> msg = wrapCommand("ADAPT_UI", data);
        messagingTemplate.convertAndSend("/topic/ui/global", msg);
        log.info("글로벌 UI 변경 통지: userType={}", uiSettings.get("userType"));
    }

    // ══════════════════════════════════════════════
    //  세션 만료 통지 (SESSION_EXPIRED)
    //
    //  Payload (문서 4.3절):
    //  {
    //    "action": "SESSION_EXPIRED",
    //    "commandId": "uuid",
    //    "data": { "message": "시간이 초과되었습니다..." }
    //  }
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
    //
    //  Payload (문서 4.3절):
    //  {
    //    "action": "VOICE_GUIDE",
    //    "commandId": "uuid",
    //    "data": {
    //      "context": "SESSION_START",
    //      "guideText": "안녕하세요...",
    //      "audioUrl": null,
    //      "lang": "ko-KR",
    //      "userType": "NORMAL"
    //    }
    //  }
    // ══════════════════════════════════════════════

    public void sendVoiceGuide(String sessionId, String guideText, String context) {
        sendVoiceGuide(sessionId, guideText, context, null, null);
    }

    public void sendVoiceGuide(String sessionId, String guideText, String context,
                                String audioUrl, String userType) {
        Map<String, Object> data = new HashMap<>();
        data.put("context", context);
        data.put("guideText", guideText);
        data.put("audioUrl", audioUrl);
        data.put("lang", "ko-KR");
        data.put("userType", userType);

        String dest = (sessionId != null && !"global".equals(sessionId))
                ? "/topic/ui/" + sessionId
                : "/topic/ui/global";

        messagingTemplate.convertAndSend(dest, wrapCommand("VOICE_GUIDE", data));
        log.debug("음성 안내 전송: sessionId={}, context={}", sessionId, context);
    }

    // ══════════════════════════════════════════════
    //  페이지 이동 (MOVE_PAGE)
    //
    //  Payload (문서 4.3절):
    //  {
    //    "action": "MOVE_PAGE",
    //    "commandId": "uuid",
    //    "data": {
    //      "pageId": 101,
    //      "sessionId": "uuid",
    //      "userType": "NORMAL"
    //    }
    //  }
    // ══════════════════════════════════════════════

    public void sendMovePage(String sessionId, Map<String, Object> pageData) {
        // sessionId가 data에 포함되지 않았다면 추가
        if (!pageData.containsKey("sessionId")) {
            pageData.put("sessionId", sessionId);
        }
        messagingTemplate.convertAndSend(
                "/topic/ui/" + sessionId, wrapCommand("MOVE_PAGE", pageData));
        log.info("페이지 이동 통지: sessionId={}, pageId={}",
                sessionId, pageData.get("pageId"));
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
    //  UI ACK 응답 (UI_ACK)
    //
    //  MCP Client가 발행한 명령(ADAPT_UI, GO_HOME 등)에 대해
    //  프론트가 ACK를 보낼 때 사용. 보통은 프론트가 직접 /app/front/ack로 보내고
    //  StompRelayController가 중계하지만, 백엔드가 직접 ACK를 발행해야 할 때 사용.
    //
    //  Payload (문서 4.4절):
    //  {
    //    "action": "UI_ACK",
    //    "data": {
    //      "commandId": "원본 commandId",
    //      "appliedAction": "ADAPT_UI"
    //    }
    //  }
    // ══════════════════════════════════════════════

    public void sendUiAck(String originalCommandId, String appliedAction) {
        Map<String, Object> data = new HashMap<>();
        data.put("commandId", originalCommandId);
        data.put("appliedAction", appliedAction);

        Map<String, Object> message = new HashMap<>();
        message.put("action", "UI_ACK");
        message.put("data", data);

        messagingTemplate.convertAndSend("/topic/front/ack", message);
        log.debug("UI ACK 발행: commandId={}, appliedAction={}",
                originalCommandId, appliedAction);
    }

    // ══════════════════════════════════════════════
    //  내부 헬퍼
    // ══════════════════════════════════════════════

    /**
     * 명령 메시지를 표준 형식으로 감싼다.
     * 모든 메시지에 action, commandId, timestamp, data 필드를 포함.
     */
    private Map<String, Object> wrapCommand(String action, Map<String, Object> data) {
        Map<String, Object> message = new HashMap<>();
        message.put("action", action);
        message.put("commandId", UUID.randomUUID().toString());
        message.put("timestamp", LocalDateTime.now().toString());
        message.put("data", data);
        return message;
    }

    /**
     * ADAPT_UI 메시지의 data 부분을 MCP 가이드 문서 형식으로 변환.
     *
     * 입력 uiSettings (SessionService 에서 만든 평탄한 Map):
     *   { userType, largeFont, highContrast, simpleMode, voiceGuide, lowScreenMode, fontSize }
     *
     * 출력 (문서 4.3절 형식):
     *   {
     *     userType: "ELDERLY",
     *     settings: { largeFont, highContrast, simpleMode, fontSize, ... }
     *   }
     */
    private Map<String, Object> buildAdaptUiData(Map<String, Object> uiSettings) {
        Map<String, Object> data = new HashMap<>();
        data.put("userType", uiSettings.get("userType"));

        Map<String, Object> settings = new HashMap<>();
        settings.put("largeFont", uiSettings.get("largeFont"));
        settings.put("highContrast", uiSettings.get("highContrast"));
        settings.put("simpleMode", uiSettings.get("simpleMode"));
        settings.put("voiceGuide", uiSettings.get("voiceGuide"));
        settings.put("lowScreenMode", uiSettings.get("lowScreenMode"));

        // fontSize를 "24px" 같은 문자열 형식으로 변환 (문서 4.3절 형식)
        Object fontSize = uiSettings.get("fontSize");
        if (fontSize instanceof Number) {
            settings.put("fontSize", fontSize + "px");
        } else {
            settings.put("fontSize", fontSize);
        }

        data.put("settings", settings);
        return data;
    }
}
