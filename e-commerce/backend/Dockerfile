FROM eclipse-temurin:21-jdk-alpine AS builder

WORKDIR /app

# Copia gradle wrapper e build files
COPY gradle gradle
COPY gradlew build.gradle settings.gradle ./

# Scarica dipendenze (layer cached)
RUN ./gradlew dependencies --no-daemon

# Copia sorgenti e builda
COPY src src
RUN ./gradlew bootJar --no-daemon

# Runtime image
FROM eclipse-temurin:21-jre-alpine

WORKDIR /app

COPY --from=builder /app/build/libs/*.jar app.jar

EXPOSE 8080

ENTRYPOINT ["java", "-jar", "app.jar"]