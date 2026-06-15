# backend-spring/Dockerfile
# Railway는 이 Dockerfile을 자동 감지해 빌드합니다.

# ── 빌드 단계: Gradle wrapper로 bootJar 생성 ──────────────
FROM eclipse-temurin:17-jdk AS build
WORKDIR /app
COPY . .
RUN chmod +x gradlew && ./gradlew bootJar --no-daemon

# ── 실행 단계: JRE만 포함한 가벼운 이미지 ─────────────────
FROM eclipse-temurin:17-jre
WORKDIR /app
COPY --from=build /app/build/libs/*.jar app.jar

# ─────────────────────────────────────────────────────────
# 메모리 튜닝 (Railway 1GB 한도 기준, 명시적 상한)
#  - Xmx512m              : 힙 상한 고정 (% 기반 ergonomics 의존 제거)
#  - MaxMetaspaceSize=128m: 메타스페이스 폭주 방지
#  - ReservedCodeCacheSize=96m : JIT 코드캐시 상한 (시간 경과 RSS 증가 차단)
#  - Xss512k              : 스레드 스택 축소 (Tomcat + WebSocket 다수 스레드)
#  - UseSerialGC          : 소형 힙에서 오버헤드 최소
#  - TieredStopAtLevel=1  : JIT 메모리/CPU 절감, 기동 가속
#  - ExitOnOutOfMemoryError : 진짜 OOM 시 즉시 종료 → Railway 재시작
# 합산 최대 RSS ≈ 512+128+96+스레드/네이티브 ≈ 850MB < 1GB
# ─────────────────────────────────────────────────────────
ENV JAVA_OPTS="-Xms128m -Xmx512m \
  -XX:MaxMetaspaceSize=128m \
  -XX:ReservedCodeCacheSize=96m \
  -Xss512k \
  -XX:+UseSerialGC \
  -XX:TieredStopAtLevel=1 \
  -XX:+ExitOnOutOfMemoryError"

ENTRYPOINT ["sh", "-c", "java $JAVA_OPTS -jar app.jar"]