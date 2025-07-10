import logging
import uuid
from typing import Optional

from open_webui.internal.db import Base, get_db
from open_webui.models.users import UserModel, Users
from open_webui.env import SRC_LOG_LEVELS
from pydantic import BaseModel
from sqlalchemy import Boolean, Column, String, Text
from open_webui.utils.auth import verify_password
from open_webui.utils import encryption_utils # Added for new encryption logic
from open_webui.utils.logger import ASSERT

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

# Note on LOCAL_HMAC_KEY:
# The encryption_utils.LOCAL_HMAC_KEY is used for deriving UserID.
# Ensure it's appropriately defined and secured in encryption_utils.py.
# For AWS deployment, this mechanism will be replaced by kms:GenerateMac.

####################
# DB MODEL
####################


class Auth(Base):
    __tablename__ = "auth"

    # The 'id' of the Auth record now corresponds to the derived UserID from the User table.
    id = Column(String, primary_key=True)

    email = Column(String)      # unused for SaaS; Enterprise may use it
    password = Column(Text)     # unused for SaaS & Enterprise
    active = Column(Boolean)


class AuthModel(BaseModel):
    id: str                     # Corresponds to UserID
    email: str
    password: str
    active: bool = True


####################
# Forms
####################


class Token(BaseModel):
    token: str
    token_type: str


class ApiKey(BaseModel):
    api_key: Optional[str] = None


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str
    profile_image_url: str


class SigninResponse(Token, UserResponse):
    pass


class SigninForm(BaseModel):
    email: str
    password: str


class LdapForm(BaseModel):
    user: str
    password: str


class ProfileImageUrlForm(BaseModel):
    profile_image_url: str


class UpdateProfileForm(BaseModel):
    profile_image_url: str
    name: str


class UpdatePasswordForm(BaseModel):
    password: str
    new_password: str


class SignupForm(BaseModel):
    name: str
    email: str
    password: str
    profile_image_url: Optional[str] = "/user.png"


class AddUserForm(SignupForm):
    role: Optional[str] = "pending"


class AuthsTable:
    def insert_new_auth(
        self,
        email: str,
        password: str,
        name: str,
        profile_image_url: str = "/user.png",
        role: str = "pending",
        oauth_sub: Optional[str] = None,
    ) -> Optional[UserModel]:
        
        # Handles the creation of a new user by:
        # 1. Deriving a UserID from the email (simulating kms:GenerateMac).
        # 2. Generating cryptographic keys (salt, UserKey, DEK, UserEncryptedDEK).
        # 3. Creating an Auth record (stores hashed password). // Only until certs & SAML are implemented.
        # 4. Creating a User record with all derived information.

        with get_db() as db:
            log.info(f"Attempting to insert new auth and user for email: {email}")

            # Step 1: Generate UserID from email using HMAC (simulates kms:GenerateMac)
            # TODO: Replace with kms:GenerateMac call in AWS environment.
            user_id_str = encryption_utils.generate_user_id(email, encryption_utils.LOCAL_HMAC_KEY)
            log.info(f"Generated UserID: {user_id_str} for email: {email}")

            # Pre-check: Ensure a user with this derived UserID doesn't already exist.
            # This is a safeguard. Email uniqueness should typically be checked by the calling route.
            # If Users.get_user_by_email was called first by router, this check might be redundant
            # but harmless if UserID collision is a concern from other sources.
            existing_user_by_id = Users.get_user_by_id(user_id_str)
            if existing_user_by_id:
                ASSERT(f"User with derived ID {user_id_str} (from email {email}) already exists.")
                return None 
                
            # Step 2: Generate salt for PBKDF2
            salt_val = encryption_utils.generate_salt()
            log.debug(f"Generated salt for UserID {salt_val}")

            # Step 3: Derive UserKey from UserID and salt using PBKDF2
            # UserKey is used to encrypt the DEK.
            user_key_val = encryption_utils.derive_key_from_user_id(user_id_str, salt_val)
            log.debug(f"Derived UserKey for UserID {user_key_val}")

            # Step 4: Generate a new Data Encryption Key (DEK)
            # DEK is used to encrypt the actual chat messages.
            dek_plaintext = encryption_utils.generate_dek()
            log.debug(f"Generated DEK for UserID {dek_plaintext}")

            # Step 5: Encrypt the DEK with the UserKey
            user_encrypted_dek_val = encryption_utils.encrypt_dek(dek_plaintext, user_key_val)
            log.debug(f"Encrypted DEK for UserID {user_encrypted_dek_val}")
            
            # Step 6: Placeholder for KMS-encrypted DEK
            # TODO: When in AWS, encrypt dek_plaintext with KMS master key and store result here.
            kms_encrypted_dek_val = None # This will be actual ciphertext from KMS in AWS.
            log.debug(f"KMS Encrypted DEK (stubbed as None) for UserID {kms_encrypted_dek_val}")

            # Create Auth table entry. Its ID is now the derived UserID.
            auth_id = user_id_str 

            auth_entry_pydantic = AuthModel(
                id=auth_id, email=email, password=password, active=True # 'password' here is the HASHED password
            )
            db_auth_entry = Auth(**auth_entry_pydantic.model_dump())
            db.add(db_auth_entry)
            log.info(f"Auth entry prepared for AuthID/UserID: {auth_id}")

            # Create User table entry, passing all derived cryptographic materials.
            # The 'user_key_val' is stored temporarily in the User table for local dev.
            # TODO: Remove 'user_key_val' storage when client certificates are implemented.
            user = Users.insert_new_user(
                id=user_id_str,
                name=name,
                email=email,
                profile_image_url=profile_image_url,
                role=role,
                oauth_sub=oauth_sub,
                salt=salt_val,
                user_key=user_key_val, # TEMPORARY storage of raw UserKey
                user_encrypted_dek=user_encrypted_dek_val,
                kms_encrypted_dek=kms_encrypted_dek_val # STUB
            )

            if user:
                log.info(f"User successfully created with UserID: {user.id}")
                db.commit() # Commit changes for both Auth and User records.
                return user
            else:
                log.error(f"User creation failed for email {email} after auth entry preparation. Rolling back.")
                db.rollback() # Rollback if Users.insert_new_user failed.
                return None

    def authenticate_user(self, email: str, password: str) -> Optional[UserModel]:
        # Authenticates a user based on email and password.
        # User.id is now the derived UserID. Auth.id also matches this UserID.
        log.info(f"authenticate_user attempt for email: {email}")

        user = Users.get_user_by_email(email)
        if not user:
            log.warning(f"Authentication failed: No user found for email {email}")
            return None

        # User.id is the derived UserID. Auth table's PK is also this UserID.
        try:
            with get_db() as db:
                auth_record = db.query(Auth).filter_by(id=user.id, active=True).first()
                if auth_record:
                    if verify_password(password, auth_record.password):
                        log.info(f"User {user.id} (email: {email}) authenticated successfully.")
                        return user
                    else:
                        log.warning(f"Authentication failed: Invalid password for user {user.id} (email: {email})")
                        return None
                else:
                    log.warning(f"Authentication failed: No active auth record found for user {user.id} (email: {email})")
                    return None
        except Exception as e:
            ASSERT(f"Exception during authentication for user {user.id} (email: {email}): {e}")
            return None

    # WE WON'T USE API KEYS FOR AUTHENTICATION IN SAAS, BUT CAN USE THIS MODEL FOR CLEINT CERTS
    def authenticate_user_by_api_key(self, api_key: str) -> Optional[UserModel]:
        log.info(f"authenticate_user_by_api_key: {api_key[:10]}...") # Log only a portion of API key
        if not api_key:
            return None

        try:
            user = Users.get_user_by_api_key(api_key)
            return user if user else None
        except Exception as e:
            ASSERT(f"Exception during API key authentication: {e}")
            return None # Changed from False to None for consistency

    def authenticate_user_by_email(self, email: str) -> Optional[UserModel]:
        # This method seems to be for cases where password is not checked (e.g. trusted header auth)
        log.info(f"authenticate_user_by_email (no password check): {email}")
        try:
            # Directly get user by email, as Auth record's utility here without password check is limited.
            # If an active Auth record is a strict requirement, the query for Auth can be kept.
            # For now, assuming if user exists, they are considered "authenticated by email" in this context.
            user = Users.get_user_by_email(email)
            if user:
                # Optionally, one could still check if db.query(Auth).filter_by(id=user.id, active=True).first() exists.
                return user
            return None
        except Exception as e:
            log.error(f"Exception during authentication by email (no password check) for {email}: {e}")
            return None

    # USERS WILL NOT HAVE THE OPTON TO CHANGE EMAILS
    def update_user_password_by_id(self, id: str, new_password: str) -> bool:
        # id here is the UserID.
        # WARNING: Changing email will change the derived UserID if re-derived.
        # This function ONLY updates the email in the Auth table.
        # The User table's email and ID are NOT changed here.
        # This could lead to inconsistencies if not handled carefully across the system.
        # TODO: Re-evaluate the need/impact of changing email post UserID derivation.
        # If email change is allowed, UserID might need to be stable or a re-keying process initiated.
        try:
            with get_db() as db:
                result = (
                    db.query(Auth).filter_by(id=id).update({"password": new_password})
                )
                db.commit()
                return True if result == 1 else False
        except Exception:
            return False

    def update_email_by_id(self, id: str, email: str) -> bool:
        try:
            with get_db() as db:
                result = db.query(Auth).filter_by(id=id).update({"email": email})
                db.commit()
                return True if result == 1 else False
        except Exception:
            return False

    def delete_auth_by_id(self, id: str) -> bool:
        try:
            with get_db() as db:
                # Delete User
                result = Users.delete_user_by_id(id)

                if result:
                    db.query(Auth).filter_by(id=id).delete()
                    db.commit()

                    return True
                else:
                    return False
        except Exception:
            return False


Auths = AuthsTable()
