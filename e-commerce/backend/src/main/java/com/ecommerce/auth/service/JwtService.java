package com.ecommerce.auth.service;

import com.ecommerce.auth.domain.User;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import jakarta.servlet.http.HttpServletRequest;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import javax.crypto.SecretKey;

import java.util.Date;

@Service
@Slf4j
@SuppressWarnings("NullableProblems")
public class JwtService {
    private final SecretKey key;
    private final long expirationMs;

    public JwtService(@Value("${app.jwt.secret}") String secret, @Value("${app.jwt.expirationMs:86400000}") long expirationMs) {
        this.key = Keys.hmacShaKeyFor(secret.getBytes());
        this.expirationMs = expirationMs;
    }

    public String generateToken(User user) {
        return Jwts.builder()
                .subject(user.getEmail())
                .claim("role", user.getRole())
                .claim("email", user.getEmail())
                .issuedAt(new Date())
                .expiration(new Date(System.currentTimeMillis() + expirationMs))
                .signWith(key)
                .compact();

    }

    public boolean validateToken(String authToken) {
        try {
            Jwts.parser().verifyWith(key).build().parseSignedClaims(authToken);
            return true;
        } catch (RuntimeException e) {
           return false;
        }
    }

    public String getEmailFromToken(String authToken) {
        try {
            return Jwts.parser().verifyWith(key).build().parseSignedClaims(authToken).getPayload().getSubject();
        } catch (RuntimeException e) {
            return null;
        }
    }

    public String getRoleFromToken(String authToken) {
        try {
            return Jwts.parser().verifyWith(key).build().parseSignedClaims(authToken).getPayload().get("role").toString();
        } catch (RuntimeException e) {
            return null;
        }
    }

    public String extractJwt(HttpServletRequest request) {
        String bearerToken = request.getHeader("Authorization");
        if (bearerToken != null && bearerToken.startsWith("Bearer ")) {
            return bearerToken.substring(7);
        }
        return null;
    }
}
