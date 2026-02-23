package com.ecommerce.auth.dto;

import com.ecommerce.auth.domain.Role;

public record AuthToken(
        String token,
        String email,
        Role role
) {
}
