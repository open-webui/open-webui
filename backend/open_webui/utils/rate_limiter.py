from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request
import logging
from typing import Callable

from open_webui.utils.auth import decode_token
from open_webui.models.users import Users

log = logging.getLogger(__name__)


def get_user_identifier(request: Request) -> str:
    """
    사용자 식별자를 반환합니다.
    인증된 사용자는 user_id, 비인증 사용자는 IP 주소 사용
    """
    try:
        # JWT 토큰에서 사용자 ID 추출
        token = None

        # Authorization 헤더에서 토큰 가져오기
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]

        # 쿠키에서 토큰 가져오기
        if not token:
            token = request.cookies.get("token")

        if token and not token.startswith("sk-"):  # API key가 아닌 경우
            data = decode_token(token)
            if data and "id" in data:
                return f"user:{data['id']}"

    except Exception as e:
        log.debug(f"Failed to extract user from token: {e}")

    # 인증 실패 시 IP 주소 사용
    return f"ip:{get_remote_address(request)}"


def get_rate_limit_key(request: Request) -> str:
    """
    사용자 역할에 따라 rate limit key를 반환합니다.
    관리자는 제한 없음을 위해 특수 키 반환
    """
    try:
        # JWT 토큰에서 사용자 정보 추출
        token = None

        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]

        if not token:
            token = request.cookies.get("token")

        if token and not token.startswith("sk-"):
            data = decode_token(token)
            if data and "id" in data:
                user = Users.get_user_by_id(data["id"])
                if user:
                    # 관리자는 무제한 (매우 높은 숫자 사용)
                    if user.role == "admin":
                        return f"admin:{user.id}"
                    # 교수
                    elif user.role == "professor":
                        return f"professor:{user.id}"
                    # 일반 사용자
                    else:
                        return f"user:{user.id}"

    except Exception as e:
        log.debug(f"Failed to get user role: {e}")

    # 비인증 사용자
    return f"guest:{get_remote_address(request)}"


# Limiter 인스턴스 생성
limiter = Limiter(
    key_func=get_user_identifier,
    default_limits=[],  # 기본값 없음 (각 엔드포인트에서 지정)
    storage_uri="memory://",  # 메모리 기반 (추후 Redis 전환 가능)
)


# 역할별 고정 제한 문자열
# 관리자는 매우 높은 한도로 사실상 무제한 (10000/분 = 분당 10000회)
# 일반 사용자/교수는 합리적인 제한
ROLE_BASED_LIMITS = "1000/minute;100/second"  # 일반 사용자도 충분히 높은 제한
WRITE_OPERATION_LIMITS = "500/minute"  # 쓰기 작업도 높은 제한


# Convenience decorators
get_role_based_limit = limiter.limit(ROLE_BASED_LIMITS)

get_write_operation_limit = limiter.limit(WRITE_OPERATION_LIMITS)
