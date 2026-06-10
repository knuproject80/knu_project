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
# bootJar 하나만 생성되므로 *.jar 매칭이 안전 (plain jar 미생성)
COPY --from=build /app/build/libs/*.jar app.jar
# server.port=${PORT} 를 통해 Railway가 주입하는 포트를 사용
ENTRYPOINT ["sh", "-c", "java -jar app.jar"]
