import json
import time
import logging
import datetime
from fastapi import APIRouter, Depends, HTTPException, Cookie, Response, Request
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from jose import JWTError
from open_webui.env import WEBUI_AUTH_COOKIE_SAME_SITE, WEBUI_AUTH_COOKIE_SECURE, SRC_LOG_LEVELS
from open_webui.utils.misc import parse_duration

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])


from open_webui.models.auths import (
    Auth,
    Auths,
    AdminMFADisableRequest,
    MFASetupResponse,
    MFAEnableResponse,
    MFAVerifyRequest,
    MFADisableResponse,
    MFABackupCodesResponse,
    PasswordConfirmRequest,
    SigninResponse,
)
from open_webui.models.users import User
from open_webui.utils.auth import get_verified_user, get_admin_user, verify_password, create_token, decode_token
from open_webui.utils.auth_mfa import (
    generate_totp_secret,
    verify_totp_code,
    generate_totp_uri,
    generate_qr_code,
    generate_backup_codes,
    hash_backup_code,
    verify_backup_code,
)
from open_webui.internal.db import get_db

router = APIRouter(prefix="/mfa", tags=["MFA Authentication"])


@router.post("/setup", response_model=MFASetupResponse)
async def setup_mfa(
    current_user: User = Depends(get_verified_user),
    db = Depends(get_db),
):
    """Initialize 2FA setup for a user"""
    with db as session:
        auth = session.query(Auth).filter_by(id=current_user.id).first()
        if auth.mfa_enabled:
            raise HTTPException(status_code=400, detail="MFA is already enabled")
    
    secret = generate_totp_secret()
    
    # Store the secret temporarily (without enabling MFA yet)
    success = Auths.setup_mfa(current_user.id, secret)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to setup MFA")
    
    # Generate TOTP URI and QR code
    uri = generate_totp_uri(secret, current_user.email)
    qr_code = generate_qr_code(uri)
    
    return {
        "secret": secret,
        "qr_code": qr_code,
    }


@router.post("/enable", response_model=MFAEnableResponse)
async def enable_mfa(
    mfa_data: MFAVerifyRequest,
    current_user: User = Depends(get_verified_user),
    db = Depends(get_db),
):
    """Verify the initial TOTP code and enable MFA"""
    # Get auth record
    with db as session:
        auth = session.query(Auth).filter_by(id=current_user.id).first()
        
        if auth.mfa_enabled:
            raise HTTPException(status_code=400, detail="MFA is already enabled")
        
        # Verify the provided code
        if not verify_totp_code(auth.mfa_secret, mfa_data.code):
            raise HTTPException(status_code=400, detail="Invalid MFA code")
    
    backup_codes = generate_backup_codes()
    hashed_backup_codes = [hash_backup_code(code) for code in backup_codes]
    

    success = Auths.enable_mfa(current_user.id, hashed_backup_codes)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to enable MFA")
    
    return {
        "enabled": True,
        "backup_codes": backup_codes,
    }


@router.post("/verify", response_model=SigninResponse)
async def verify_mfa(
    request: Request,
    mfa_data: MFAVerifyRequest,
    partial_token: str = Cookie(None, alias="partial_token"),
    db = Depends(get_db),
):
    """Verify TOTP code during login and complete authentication"""

    client_ip = request.client.host
    
    # Must have a partial token from the first authentication step
    if not partial_token:
        log.warning(f"[MFA ERROR] MFA verification attempted without partial_token from IP: {client_ip}")
        raise HTTPException(status_code=401, detail="No partial authentication")
    
    log.info(f"Verifying MFA code (length: {len(mfa_data.code)}) from IP: {client_ip}")
    try:
        # Decode partial token (contains user ID but is marked as MFA-pending)
        payload = decode_token(partial_token)
        log.debug(f"[MFA DEBUG] Partial token payload: {payload}")
        
        if not payload or not payload.get("mfa_required"):
            log.warning(f"[MFA ERROR] Invalid partial token used in MFA verification from IP: {client_ip}")
            raise HTTPException(status_code=400, detail="Invalid partial token")
        
        # Get user ID - check both fields for compatibility
        user_id = payload.get("id") or payload.get("sub")
        log.debug(f"[MFA DEBUG] User ID from token: {user_id}")
        
        if not user_id:
            log.warning(f"[MFA ERROR] Token missing user identifier in MFA verification from IP: {client_ip}")
            raise HTTPException(status_code=400, detail="Token missing user identifier")
        

        with db as session:
            auth = session.query(Auth).filter_by(id=user_id).first()
            user = session.query(User).filter_by(id=user_id).first()
            
            if not auth or not user:
                log.warning(f"User not found during MFA verification for user_id: {user_id} from IP: {client_ip}")
                raise HTTPException(status_code=404, detail="User not found")
        
            is_backup = False
            verification_success = False
            
            if len(mfa_data.code) > 6 and "-" in mfa_data.code:
                # This might be a backup code
                backup_codes = json.loads(auth.backup_codes) if auth.backup_codes else []
                hashed = verify_backup_code(mfa_data.code, backup_codes)
                if not hashed:
                    log.warning(f"Invalid backup code provided for user {user_id} from IP: {client_ip}")
                    
                    raise HTTPException(status_code=400, detail="Authentication failed. Please check your code and try again.")
                
                # Remove this backup code - it's one-time use
                success = Auths.use_backup_code(user_id, hashed)
                if not success:
                    log.error(f"Failed to process backup code for user {user_id} from IP: {client_ip}")
                    raise HTTPException(status_code=500, detail="Failed to process backup code")
                
                is_backup = True
                verification_success = True
            else:
                # This is a TOTP code
                if not verify_totp_code(auth.mfa_secret, mfa_data.code):
                    log.warning(f"Invalid TOTP code provided for user {user_id} from IP: {client_ip}")

                    
                    raise HTTPException(
                        status_code=400, 
                        detail="Authentication failed. Please check your verification code and try again."
                    )
                
                Auths.update_mfa_last_used(user_id)
                verification_success = True
        
        if verification_success:
            
            # Create token with "id" field for compatibility with auth middleware
            log.info(f"Creating full auth token for user {user.id} after successful MFA verification")
            access_token = create_token(data={"id": user.id})

            response = SigninResponse(
                token=access_token,
                token_type="bearer",
                id=user.id,
                email=user.email,
                name=user.name,
                role=user.role,
                profile_image_url=user.profile_image_url,
                is_backup_code_used=is_backup
            )
            
            # Use identical cookie settings as in standard auth flow for consistency
            response_json = JSONResponse(content=jsonable_encoder(response))
            log.info(f"Setting auth cookie after MFA verification for user {user.id}")
            
            # Calculate expiration based on standard auth approach
            expires_at = None
            expires_delta = parse_duration("30d")  # Default to 30 days if not specified
            if expires_delta:
                expires_at = int(time.time()) + int(expires_delta.total_seconds())
                
            datetime_expires_at = (
                datetime.datetime.fromtimestamp(expires_at, datetime.timezone.utc)
                if expires_at
                else None
            )

            response_json.set_cookie(
                key="token",
                value=access_token,
                expires=datetime_expires_at,
                httponly=True,  # Ensures the cookie is not accessible via JavaScript
                samesite=WEBUI_AUTH_COOKIE_SAME_SITE,
                secure=WEBUI_AUTH_COOKIE_SECURE,
            )
            
            response_json.delete_cookie(key="partial_token")
            
            return response_json
    except JWTError:
        log.warning(f"JWT error during MFA verification from IP: {client_ip}")
        raise HTTPException(status_code=401, detail="Invalid partial token")


@router.post("/disable", response_model=MFADisableResponse)
async def disable_mfa(
    request: Request,
    password_data: PasswordConfirmRequest,
    current_user: User = Depends(get_verified_user),
    db = Depends(get_db),
):
    """Disable MFA after confirming both password and MFA code"""
    client_ip = request.client.host

    
    with db as session:
        auth = session.query(Auth).filter_by(id=current_user.id).first()
        
        if not auth.mfa_enabled:
            raise HTTPException(status_code=400, detail="MFA is not enabled")
        
        if not verify_password(password_data.password, auth.password):
            log.warning(f"Invalid password provided by user {current_user.id} when disabling MFA from IP: {client_ip}")
            # Rate limiting account lockout tracking removed
            raise HTTPException(status_code=400, detail="Authentication failed. Please check your credentials and try again.")
        
        if not password_data.code:
            raise HTTPException(status_code=400, detail="Verification code is required to disable 2FA")
        
        if not verify_totp_code(auth.mfa_secret, password_data.code):
            log.warning(f"Invalid MFA code provided by user {current_user.id} when disabling MFA from IP: {client_ip}")
            raise HTTPException(status_code=400, detail="Authentication failed. Please check your verification code and try again.")

    
    success = Auths.disable_mfa(current_user.id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to disable MFA")
    
    log.info(f"MFA disabled for user {current_user.id} from IP: {client_ip}")
    return {"disabled": True}


@router.post("/backup-codes", response_model=MFABackupCodesResponse)
async def regenerate_backup_codes(
    request: Request,
    password_data: PasswordConfirmRequest,
    current_user: User = Depends(get_verified_user),
    db = Depends(get_db),
):
    """Regenerate backup codes after confirming password"""
    client_ip = request.client.host

    
    with db as session:
        auth = session.query(Auth).filter_by(id=current_user.id).first()
        
        if not auth.mfa_enabled:
            raise HTTPException(status_code=400, detail="MFA is not enabled")
        
        # Verify password - don't reveal whether password specifically is invalid
        if not verify_password(password_data.password, auth.password):
            log.warning(f"Invalid password provided by user {current_user.id} when regenerating backup codes from IP: {client_ip}")
            
            
            raise HTTPException(status_code=400, detail="Authentication failed. Please check your credentials and try again.")
    

    backup_codes = generate_backup_codes()
    hashed_backup_codes = [hash_backup_code(code) for code in backup_codes]

    success = Auths.update_backup_codes(current_user.id, hashed_backup_codes)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update backup codes")
    
    log.info(f"Backup codes regenerated for user {current_user.id} from IP: {client_ip}")
    return {"backup_codes": backup_codes}

@router.post("/admin/disable", response_model=MFADisableResponse)
async def admin_disable_mfa(
    request: Request,
    disable_data: AdminMFADisableRequest,
    admin_user: User = Depends(get_admin_user),
    db = Depends(get_db),
):
    """Admin endpoint to disable MFA for any user"""
    client_ip = request.client.host
    target_user_id = disable_data.user_id

    with db as session:
        target_auth = session.query(Auth).filter_by(id=target_user_id).first()
        target_user = session.query(User).filter_by(id=target_user_id).first()
        
        if not target_auth or not target_user:
            log.warning(f"Admin attempted to disable MFA for non-existent user ID: {target_user_id} from IP: {client_ip}")
            raise HTTPException(status_code=404, detail="User not found")

        if not target_auth.mfa_enabled:
            raise HTTPException(status_code=400, detail="MFA is not enabled for this user")
    

    success = Auths.disable_mfa(target_user_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to disable MFA")
    
    log.info(f"MFA disabled for user {target_user_id} by admin {admin_user.id} from IP: {client_ip}")
    return {"disabled": True}
