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
# 메모리 튜닝 (Railway 소형 컨테이너에서 OOM 방지)
#  - MaxRAMPercentage=70 : 컨테이너 한도의 70%까지만 힙으로 사용
#  - UseSerialGC          : 소형 힙에서 G1보다 메모리 오버헤드가 훨씬 작음
#  - Xss512k              : 스레드 스택 축소 (Tomcat + WebSocket 스레드 다수)
#  - MaxMetaspaceSize     : 메타스페이스 폭주 방지
#  - TieredStopAtLevel=1  : JIT 컴파일러 메모리/CPU 절감 (기동도 빨라짐)
# 컨테이너 메모리가 늘어나면 JVM이 비율로 자동 조정됩니다.
# ─────────────────────────────────────────────────────────
ENV JAVA_OPTS="-XX:MaxRAMPercentage=70.0 -XX:+UseSerialGC -Xss512k -XX:MaxMetaspaceSize=128m -XX:TieredStopAtLevel=1"

ENTRYPOINT ["sh", "-c", "java $JAVA_OPTS -jar app.jar"]
