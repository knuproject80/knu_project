package com.kiosk.websocket;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.messaging.handler.annotation.MessageMapping;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.stereotype.Controller;

import java.util.Map;

/**
 * STOMP 메시지 중계 컨트롤러.
 *
 * Spring 기본 SimpleBroker는 서버→클라이언트 전송만 지원하므로,
 * 프론트가 발행한 메시지를 다른 클라이언트(MCP Client 등)에게 전달하려면
 * 서버가 한 번 받아서 다시 broadcast 해야 한다.
 *
 * 클라이언트는 /app/front/events 또는 /app/front/ack 로 SEND 한다.
 *   (Spring @MessageMapping prefix 가 /app 이므로)
 *
 * 서버는 받은 메시지를 그대로 /topic/front/events, /topic/front/ack 로 중계한다.
 *   (구독자들이 받을 수 있도록)
 *
 * MCP Client 테스트 가이드 문서 4.1 절, 5.1 절에 정의된 토픽 구조를 지원하기 위한 컴포넌트.
 */
@Controller
public class StompRelayController {

    private static final Logger log = LoggerFactory.getLogger(StompRelayController.class);

    private final SimpMessagingTemplate messagingTemplate;

    public StompRelayController(SimpMessagingTemplate messagingTemplate) {
        this.messagingTemplate = messagingTemplate;
    }

    // ══════════════════════════════════════════════
    //  프론트 → 백엔드 → MCP Client 중계
    //
    //  프론트 SEND: /app/front/events
    //  → 백엔드가 받음
    //  → /topic/front/events 로 다시 broadcast
    //  → MCP Client(구독 중)가 수신
    //
    //  지원하는 action:
    //  - VOICE_INPUT     : 음성 입력 결과 (STT)
    //  - USER_TOUCH      : 사용자 조작 (idle 타이머 갱신)
    //  - STEP_CHANGE     : 단계 전환
    //  - SERVICE_COMPLETE: 서비스 완료
    //  - USER_CANCEL     : 사용자 취소
    // ══════════════════════════════════════════════

    @MessageMapping("/front/events")
    public void relayFrontEvents(Map<String, Object> message) {
        String action = (String) message.get("action");
        log.info("프론트 이벤트 중계: action={}", action);
        messagingTemplate.convertAndSend("/topic/front/events", message);
    }

    // ══════════════════════════════════════════════
    //  프론트 → 백엔드 → MCP Client ACK 응답 중계
    //
    //  프론트 SEND: /app/front/ack
    //  → 백엔드가 받음
    //  → /topic/front/ack 로 다시 broadcast
    //  → MCP Client(구독 중)가 ACK 수신
    //
    //  Payload 예시:
    //  {
    //    "action": "UI_ACK",
    //    "data": {
    //      "commandId": "원본 commandId",
    //      "appliedAction": "ADAPT_UI"
    //    }
    //  }
    // ══════════════════════════════════════════════

    @MessageMapping("/front/ack")
    public void relayFrontAck(Map<String, Object> message) {
        Object data = message.get("data");
        log.debug("프론트 ACK 중계: {}", data);
        messagingTemplate.convertAndSend("/topic/front/ack", message);
    }
}
