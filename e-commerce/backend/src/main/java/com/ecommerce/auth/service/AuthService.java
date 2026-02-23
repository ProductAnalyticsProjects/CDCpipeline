package com.ecommerce.auth.service;


import com.ecommerce.auth.domain.Role;
import com.ecommerce.auth.domain.User;
import com.ecommerce.auth.dto.AuthToken;
import com.ecommerce.auth.dto.LoginRequest;
import com.ecommerce.auth.dto.RegisterRequest;
import com.ecommerce.auth.repository.UserRepository;
import com.ecommerce.common.exception.BusinessException;
import com.ecommerce.common.exception.ResourceNotFoundException;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.jspecify.annotations.Nullable;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

@Service
@Slf4j
@SuppressWarnings("NullableProblems")
public class AuthService {
    private final JwtService jwtService;
    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;

    public AuthService(JwtService jwtService, UserRepository userRepository, PasswordEncoder passwordEncoder) {
        this.jwtService = jwtService;
        this.userRepository = userRepository;
        this.passwordEncoder = passwordEncoder;
    }
    public String encode(String rawPassword) {
        return passwordEncoder.encode(rawPassword);
    }

    public boolean matches(String rawPassword, @Nullable String encodedPassword) {
        return passwordEncoder.matches(rawPassword, encodedPassword);
    }


    public AuthToken login(LoginRequest loginRequest) {
        var user = userRepository.findByEmail(loginRequest.email())
                .orElseThrow(() -> new BusinessException("INVALID_CREDENTIALS", "Invalid email or password"));

        if (!matches(loginRequest.password(), user.getPasswordHash())) {
            throw new BusinessException("INVALID_CREDENTIALS", "Invalid email or password");
        }

        String token = jwtService.generateToken(user);
        return new AuthToken(token, user.getEmail(), user.getRole());
    }


    public AuthToken register(RegisterRequest registerRequest) {
        if (!userRepository.existsByEmail(registerRequest.email())) {
            String hashedPassword = encode(registerRequest.password());
            User newUser = new User(
                    registerRequest.email(),
                    hashedPassword,
                    Role.CUSTOMER
            );
            User saved = userRepository.save(newUser);
            return login(new LoginRequest(saved.getEmail(), registerRequest.password()));
        }
        throw new BusinessException("EMAIL_EXISTS", "Email already registered");
    }


}
