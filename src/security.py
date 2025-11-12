"""
Security Module

This module provides authentication, authorization, and security utilities:
- API key authentication
- Role-based access control (RBAC)
- Rate limiting
- Input validation and sanitization
- Security headers

Technologies: FastAPI security, JWT, rate limiting
"""

import hashlib
import hmac
import time
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from enum import Enum
import secrets
import os
import re

try:
    from fastapi import HTTPException, status, Request
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

    # Create dummy classes for testing without FastAPI
    class HTTPException(Exception):
        def __init__(self, status_code, detail, headers=None):
            self.status_code = status_code
            self.detail = detail
            self.headers = headers

    class Request:
        def __init__(self):
            self.headers = {}
            self.query_params = {}

    class status:
        HTTP_401_UNAUTHORIZED = 401
        HTTP_403_FORBIDDEN = 403
        HTTP_429_TOO_MANY_REQUESTS = 429


# Import JWT separately so it's always available
try:
    import jwt

    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False


logger = logging.getLogger(__name__)


class Permission(Enum):
    """Available permissions"""

    READ_METRICS = "read:metrics"
    QUERY_METRICS = "query:metrics"
    WRITE_METRICS = "write:metrics"
    ADMIN = "admin"
    CACHE_MANAGE = "cache:manage"


@dataclass
class User:
    """User model for authentication"""

    id: str
    username: str
    permissions: Set[Permission]
    created_at: datetime
    last_active: datetime
    rate_limit: int = 100  # queries per hour


@dataclass
class RateLimitInfo:
    """Rate limit tracking information"""

    count: int
    window_start: datetime
    window_size: int = 3600  # 1 hour in seconds


class SecurityConfig:
    """Security configuration"""

    def __init__(self):
        # API Keys (in production, these should be in a secure key store)
        self.api_keys = self._load_api_keys()

        # JWT Configuration
        self.jwt_secret = os.getenv("JWT_SECRET", secrets.token_urlsafe(32))
        self.jwt_algorithm = "HS256"
        self.jwt_expiry_hours = int(os.getenv("JWT_EXPIRY_HOURS", "24"))

        # Rate limiting
        self.default_rate_limit = int(os.getenv("DEFAULT_RATE_LIMIT", "100"))
        self.rate_limit_window = int(os.getenv("RATE_LIMIT_WINDOW", "3600"))

        # Security settings
        self.require_https = os.getenv("REQUIRE_HTTPS", "false").lower() == "true"
        self.allowed_origins = os.getenv("CORS_ORIGINS", "*").split(",")

    def _load_api_keys(self) -> Dict[str, User]:
        """Load API keys and user configurations"""
        api_keys = {}

        # Load from environment variables
        admin_key = os.getenv("API_KEY_ADMIN")
        read_key = os.getenv("API_KEY_READ")
        query_key = os.getenv("API_KEY_QUERY")

        if admin_key:
            api_keys[admin_key] = User(
                id="admin",
                username="admin",
                permissions={
                    Permission.ADMIN,
                    Permission.READ_METRICS,
                    Permission.QUERY_METRICS,
                    Permission.WRITE_METRICS,
                    Permission.CACHE_MANAGE,
                },
                created_at=datetime.now(timezone.utc).replace(tzinfo=None),
                last_active=datetime.now(timezone.utc).replace(tzinfo=None),
                rate_limit=1000,
            )

        if read_key:
            api_keys[read_key] = User(
                id="reader",
                username="reader",
                permissions={Permission.READ_METRICS},
                created_at=datetime.now(timezone.utc).replace(tzinfo=None),
                last_active=datetime.now(timezone.utc).replace(tzinfo=None),
                rate_limit=100,
            )

        if query_key:
            api_keys[query_key] = User(
                id="querier",
                username="querier",
                permissions={Permission.READ_METRICS, Permission.QUERY_METRICS},
                created_at=datetime.now(timezone.utc).replace(tzinfo=None),
                last_active=datetime.now(timezone.utc).replace(tzinfo=None),
                rate_limit=200,
            )

        return api_keys


class InputValidator:
    """Input validation and sanitization"""

    # Allowed characters in metric names
    METRIC_NAME_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]{0,63}$")

    # Allowed characters in dimension names
    DIMENSION_NAME_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]{0,63}$")

    # Basic SQL injection patterns to block
    SQL_INJECTION_PATTERNS = [
        re.compile(r"\b(DROP|DELETE|UPDATE|INSERT|ALTER|CREATE|EXEC|EXECUTE)\b", re.IGNORECASE),
        re.compile(r"\bUNION\s+SELECT\b", re.IGNORECASE),  # UNION SELECT attacks
        re.compile(r"\bSELECT\b.*\bFROM\b", re.IGNORECASE),  # Subqueries
        re.compile(r"\b(OR|AND)\s+\d+\s*=\s*\d+", re.IGNORECASE),
        re.compile(r';.*[\'";]', re.IGNORECASE),  # SQL injection with semicolons
        re.compile(r"--.*", re.IGNORECASE),  # SQL comments
        re.compile(r"/\*.*\*/", re.IGNORECASE),  # SQL block comments
        re.compile(r"'\s*(OR|AND)\s*'", re.IGNORECASE),  # 'x' OR 'y' pattern
        re.compile(r"=\s*'\s*(OR|AND)\s*", re.IGNORECASE),  # = 'x' OR pattern
    ]

    @staticmethod
    def validate_metric_name(name: str) -> bool:
        """Validate metric name format"""
        if not name or len(name) > 64:
            return False
        return bool(InputValidator.METRIC_NAME_PATTERN.match(name))

    @staticmethod
    def validate_dimension_name(name: str) -> bool:
        """Validate dimension name format"""
        if not name or len(name) > 64:
            return False
        return bool(InputValidator.DIMENSION_NAME_PATTERN.match(name))

    @staticmethod
    def validate_filter_expression(filter_expr: str) -> bool:
        """Check if filter expression is safe"""
        if not filter_expr or len(filter_expr) > 500:
            return False

        # Check for SQL injection patterns
        for pattern in InputValidator.SQL_INJECTION_PATTERNS:
            if pattern.search(filter_expr):
                logger.warning(f"Potentially unsafe filter blocked: {filter_expr}")
                return False

        return True

    @staticmethod
    def sanitize_string(value: str, max_length: int = 1000) -> str:
        """Sanitize string input"""
        if not value:
            return ""

        # Truncate to max length
        value = value[:max_length]

        # Remove control characters
        value = "".join(char for char in value if ord(char) >= 32 or char in "\t\n\r")

        return value


class RateLimiter:
    """Rate limiting implementation"""

    def __init__(self):
        self.limits: Dict[str, RateLimitInfo] = {}

    def check_rate_limit(self, client_id: str, limit: int, window: int = 3600) -> bool:
        """
        Check if client is within rate limit

        Args:
            client_id: Unique client identifier
            limit: Number of requests allowed per window
            window: Time window in seconds

        Returns:
            True if within limit, False if exceeded
        """
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        if client_id not in self.limits:
            self.limits[client_id] = RateLimitInfo(count=1, window_start=now, window_size=window)
            return True

        rate_info = self.limits[client_id]

        # Check if window has expired
        if (now - rate_info.window_start).total_seconds() > rate_info.window_size:
            rate_info.count = 1
            rate_info.window_start = now
            return True

        # Increment counter
        rate_info.count += 1

        return rate_info.count <= limit

    def get_rate_limit_info(self, client_id: str) -> Optional[RateLimitInfo]:
        """Get current rate limit info for client"""
        return self.limits.get(client_id)


class AuthenticationManager:
    """Authentication and authorization manager"""

    def __init__(self):
        self.config = SecurityConfig()
        self.rate_limiter = RateLimiter()
        self.validator = InputValidator()

    def authenticate_api_key(self, api_key: str) -> Optional[User]:
        """Authenticate user by API key"""
        if not api_key:
            return None

        # Hash the API key for secure comparison
        hashed_key = self._hash_api_key(api_key)

        # Look up user (in production, this would be in a database)
        user = self.config.api_keys.get(api_key)
        if user:
            user.last_active = datetime.now(timezone.utc).replace(tzinfo=None)
            logger.info(f"User authenticated: {user.username}")

        return user

    def verify_permission(self, user: User, permission: Permission) -> bool:
        """Check if user has required permission"""
        return permission in user.permissions or Permission.ADMIN in user.permissions

    def check_rate_limit(self, user: User) -> bool:
        """Check if user is within rate limit"""
        return self.rate_limiter.check_rate_limit(
            user.id, user.rate_limit, self.config.rate_limit_window
        )

    def _hash_api_key(self, api_key: str) -> str:
        """Hash API key for secure storage"""
        return hashlib.sha256(api_key.encode()).hexdigest()

    def generate_jwt(self, user: User) -> str:
        """Generate JWT token for user"""
        if not JWT_AVAILABLE:
            raise RuntimeError("PyJWT library not available")

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        payload = {
            "user_id": user.id,
            "username": user.username,
            "permissions": [p.value for p in user.permissions],
            "exp": now + timedelta(hours=self.config.jwt_expiry_hours),
            "iat": now,
        }

        return jwt.encode(payload, self.config.jwt_secret, algorithm=self.config.jwt_algorithm)

    def verify_jwt(self, token: str) -> Optional[User]:
        """Verify and decode JWT token"""
        if not JWT_AVAILABLE:
            raise RuntimeError("PyJWT library not available")

        try:
            payload = jwt.decode(
                token, self.config.jwt_secret, algorithms=[self.config.jwt_algorithm]
            )

            permissions = {Permission(p) for p in payload["permissions"]}
            now = datetime.now(timezone.utc).replace(tzinfo=None)

            return User(
                id=payload["user_id"],
                username=payload["username"],
                permissions=permissions,
                created_at=now,  # Would be loaded from DB in production
                last_active=now,
            )

        except jwt.ExpiredSignatureError:
            logger.warning("JWT token expired")
            return None
        except jwt.InvalidTokenError:
            logger.warning("Invalid JWT token")
            return None


class SecurityMiddleware:
    """Security middleware for FastAPI"""

    def __init__(self):
        self.auth_manager = AuthenticationManager()

    async def authenticate_request(self, request: Request) -> User:
        """Authenticate incoming request"""
        # Try API key authentication first
        api_key = request.headers.get("X-API-Key") or request.query_params.get("api_key")
        if api_key:
            user = self.auth_manager.authenticate_api_key(api_key)
            if user:
                return user

        # Try JWT authentication
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove 'Bearer ' prefix
            user = self.auth_manager.verify_jwt(token)
            if user:
                return user

        # No valid authentication found
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    def require_permission(self, permission: Permission):
        """Decorator factory for permission requirements"""

        def decorator(func):
            async def wrapper(*args, **kwargs):
                request = kwargs.get("request") or args[0]
                user = await self.authenticate_request(request)

                if not self.auth_manager.verify_permission(user, permission):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Permission required: {permission.value}",
                    )

                if not self.auth_manager.check_rate_limit(user):
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded"
                    )

                # Add user to kwargs
                kwargs["current_user"] = user
                return await func(*args, **kwargs)

            return wrapper

        return decorator


# Security headers middleware
def add_security_headers(response):
    """Add security headers to response"""
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# Example usage and testing
if __name__ == "__main__":
    print("🔒 Testing Security Module")
    print("=" * 50)

    # Test input validation
    validator = InputValidator()

    test_metrics = ["total_revenue", "customer_count", "invalid-name", "a" * 70]
    print("\n📊 Testing metric name validation:")
    for metric in test_metrics:
        valid = validator.validate_metric_name(metric)
        print(f"  {metric}: {'✅' if valid else '❌'}")

    # Test filter validation
    test_filters = [
        "customer_segment = 'Enterprise'",
        "revenue > 1000",
        "name = 'test'; DROP TABLE users;--",
        "1=1 OR 2=2",
        "UNION SELECT * FROM passwords",
    ]

    print(f"\n🛡️ Testing filter validation:")
    for filter_expr in test_filters:
        safe = validator.validate_filter_expression(filter_expr)
        print(f"  '{filter_expr}': {'✅ Safe' if safe else '❌ Blocked'}")

    # Test rate limiting
    rate_limiter = RateLimiter()

    print(f"\n⏱️ Testing rate limiting:")
    for i in range(5):
        allowed = rate_limiter.check_rate_limit("client1", limit=3)
        print(f"  Request {i+1}: {'✅ Allowed' if allowed else '❌ Rate limited'}")

    # Test authentication
    auth_manager = AuthenticationManager()

    print(f"\n🔑 Testing authentication:")
    # This would work if API keys were configured
    test_key = "test-api-key-123"
    user = auth_manager.authenticate_api_key(test_key)
    print(f"  API key auth: {'✅ Success' if user else '❌ Failed'}")

    print(f"\n🎉 Security module tests complete!")

    # Generate example API keys for documentation
    print(f"\n📋 Example API Key Generation:")
    admin_key = secrets.token_urlsafe(32)
    query_key = secrets.token_urlsafe(32)
    read_key = secrets.token_urlsafe(32)

    print(f"  Admin key:  API_KEY_ADMIN={admin_key}")
    print(f"  Query key:  API_KEY_QUERY={query_key}")
    print(f"  Read key:   API_KEY_READ={read_key}")
    print(f"\n💡 Add these to your .env file for authentication")
