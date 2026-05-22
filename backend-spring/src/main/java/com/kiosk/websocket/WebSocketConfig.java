package com.kiosk.websocket;

import org.springframework.context.annotation.Configuration;
import org.springframework.messaging.simp.config.MessageBrokerRegistry;
import org.springframework.web.socket.config.annotation.EnableWebSocketMessageBroker;
import org.springframework.web.socket.config.annotation.StompEndpointRegistry;
import org.springframework.web.socket.config.annotation.WebSocketMessageBrokerConfigurer;

/**
 * WebSocket / STOMP 설정.
 *
 * MCP Client 테스트 가이드 문서 기준 토픽 구조:
 *
 *  서버 → 클라이언트 (구독 가능, prefix: /topic):
 *   - /topic/ui/{sessionId}  : 세션별 UI 명령 (ADAPT_UI, MOVE_PAGE, VOICE_GUIDE, GO_HOME, SESSION_EXPIRED)
 *   - /topic/ui/global       : 글로벌 UI 명령
 *   - /topic/ai/{sessionId}  : AI 응답
 *   - /topic/front/events    : 프론트 이벤트 (StompRelayController 중계)
 *   - /topic/front/ack       : 프론트 ACK (StompRelayController 중계)
 *
 *  클라이언트 → 서버 (전송, prefix: /app):
 *   - /app/front/events      : 프론트가 발행하는 이벤트 (서버가 /topic/front/events 로 중계)
 *   - /app/front/ack         : 프론트가 발행하는 ACK (서버가 /topic/front/ack 로 중계)
 */
@Configuration
@EnableWebSocketMessageBroker
public class WebSocketConfig implements WebSocketMessageBrokerConfigurer {

    @Override
    public void configureMessageBroker(MessageBrokerRegistry config) {
        // 구독 가능한 prefix (서버 → 클라이언트)
        config.enableSimpleBroker("/topic");

        // 클라이언트→서버 전송 prefix (SimpMessagingTemplate 의 @MessageMapping 라우팅 대상)
        config.setApplicationDestinationPrefixes("/app");
    }

    @Override
    public void registerStompEndpoints(StompEndpointRegistry registry) {
        // STOMP heartbeat 10초 / 10초 (문서 4. 절 기준)
        // SockJS fallback 지원 (브라우저용)
        registry.addEndpoint("/ws")
                .setAllowedOriginPatterns("*")
                .withSockJS();

        // 순수 WebSocket (MCP Client stomp_manager 등 non-SockJS 클라이언트용)
        registry.addEndpoint("/ws")
                .setAllowedOriginPatterns("*");
    }
}
