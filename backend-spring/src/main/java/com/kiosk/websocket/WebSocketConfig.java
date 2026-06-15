package com.kiosk.websocket;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.messaging.simp.config.MessageBrokerRegistry;
import org.springframework.scheduling.concurrent.ThreadPoolTaskScheduler;
import org.springframework.web.socket.config.annotation.EnableWebSocketMessageBroker;
import org.springframework.web.socket.config.annotation.StompEndpointRegistry;
import org.springframework.web.socket.config.annotation.WebSocketMessageBrokerConfigurer;
import org.springframework.web.socket.config.annotation.WebSocketTransportRegistration;

/**
 * WebSocket / STOMP 설정.
 *
 * MCP Client 테스트 가이드 문서 4절 기준:
 *   - WebSocket URL: ws://localhost:8080/ws
 *   - STOMP 버전: 1.2 / heart-beat: 10000,10000 (10초)
 *
 * 토픽 구조:
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
        // STOMP heartbeat 10초/10초 활성화 (문서 4절 기준)
        config.enableSimpleBroker("/topic")
                .setHeartbeatValue(new long[]{10000, 10000})
                .setTaskScheduler(heartBeatScheduler());

        // 클라이언트→서버 전송 prefix (SimpMessagingTemplate 의 @MessageMapping 라우팅 대상)
        config.setApplicationDestinationPrefixes("/app");
    }

    @Override
    public void registerStompEndpoints(StompEndpointRegistry registry) {
        // SockJS fallback 지원 (브라우저용)
        registry.addEndpoint("/ws")
                .setAllowedOriginPatterns("*")
                .withSockJS();

        // 순수 WebSocket (MCP Client stomp_manager 등 non-SockJS 클라이언트용)
        registry.addEndpoint("/ws")
                .setAllowedOriginPatterns("*");
    }

    /**
     * WebSocket transport 제한 — native/off-heap 메모리 누수 방지.
     *
     * 느리거나 응답 없는(좀비) 연결이 서버 송신 버퍼를 무한정 쌓는 것을 막는다.
     * 한도를 넘는 세션은 Spring 이 강제로 닫아 버퍼를 회수하므로,
     * 며칠에 걸쳐 RSS 가 서서히 차오르는 현상을 차단한다.
     *
     *  - messageSizeLimit   : 수신 메시지 1건의 최대 크기 (64KB)
     *                          이 앱의 메시지는 작은 JSON 이라 충분.
     *  - sendBufferSizeLimit: 세션당 송신 대기 버퍼 상한 (512KB)
     *                          느린 소비자가 이 한도를 넘으면 세션을 닫는다.
     *  - sendTimeLimit      : 메시지 1건 전송 제한 시간 (20초)
     *                          이 시간 안에 못 보내면(죽은 연결) 세션을 닫는다.
     */
    @Override
    public void configureWebSocketTransport(WebSocketTransportRegistration registration) {
        registration.setMessageSizeLimit(64 * 1024);        // 64 KB
        registration.setSendBufferSizeLimit(512 * 1024);    // 512 KB
        registration.setSendTimeLimit(20 * 1000);           // 20 초
    }

    /**
     * STOMP heartbeat 전송을 위한 TaskScheduler.
     * SimpleBroker가 heartbeat 메시지를 주기적으로 보내려면 TaskScheduler가 필요하다.
     */
    @Bean
    public ThreadPoolTaskScheduler heartBeatScheduler() {
        ThreadPoolTaskScheduler scheduler = new ThreadPoolTaskScheduler();
        scheduler.setPoolSize(1);
        scheduler.setThreadNamePrefix("stomp-heartbeat-");
        scheduler.initialize();
        return scheduler;
    }
}
