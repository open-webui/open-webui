import time
import uuid
from typing import Optional

from open_webui.internal.db import Base, get_db
from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, String, Text, Index

####################
# CHILD PROFILE: Database schema for storing child profiles linked to parent users
# - Stores child profile information for kids mode
# - Links child profiles to parent user accounts
# - Supports multiple children per parent
####################

class ChildProfile(Base):
    __tablename__ = "child_profile"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)  # Link to parent user
    name = Column(String, nullable=False)  # Child's name
    child_age = Column(String, nullable=True)  # Age range (e.g., "5-7", "8-10")
    child_gender = Column(String, nullable=True)  # Gender (e.g., "Male", "Female")
    child_characteristics = Column(Text, nullable=True)  # Personality/interests description
    parenting_style = Column(String, nullable=True)  # Parenting approach/preferences
    
    created_at = Column(BigInteger)  # When profile was created
    updated_at = Column(BigInteger)  # When profile was last updated

    # Indexes for efficient querying
    __table_args__ = (
        Index('idx_child_profile_user_id', 'user_id'),
        Index('idx_child_profile_created_at', 'created_at'),
    )

class ChildProfileModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    user_id: str
    name: str
    child_age: Optional[str] = None
    child_gender: Optional[str] = None
    child_characteristics: Optional[str] = None
    parenting_style: Optional[str] = None
    created_at: int
    updated_at: int

class ChildProfileForm(BaseModel):
    name: str
    child_age: Optional[str] = None
    child_gender: Optional[str] = None
    child_characteristics: Optional[str] = None
    parenting_style: Optional[str] = None

class ChildProfileTable:
    def insert_new_child_profile(
        self, form_data: ChildProfileForm, user_id: str
    ) -> Optional[ChildProfileModel]:
        """Insert a new child profile into the database"""
        with get_db() as db:
            id = str(uuid.uuid4())
            ts = int(time.time_ns())
            
            child_profile = ChildProfileModel(
                **{
                    "id": id,
                    "user_id": user_id,
                    "name": form_data.name,
                    "child_age": form_data.child_age,
                    "child_gender": form_data.child_gender,
                    "child_characteristics": form_data.child_characteristics,
                    "parenting_style": form_data.parenting_style,
                    "created_at": ts,
                    "updated_at": ts,
                }
            )
            
            result = ChildProfile(**child_profile.model_dump())
            db.add(result)
            db.commit()
            db.refresh(result)
            return ChildProfileModel.model_validate(result) if result else None

    def get_child_profiles_by_user(self, user_id: str) -> list[ChildProfileModel]:
        """Get all child profiles for a specific parent user"""
        with get_db() as db:
            profiles = db.query(ChildProfile).filter(
                ChildProfile.user_id == user_id
            ).order_by(ChildProfile.created_at.asc()).all()
            
            return [ChildProfileModel.model_validate(profile) for profile in profiles]

    def get_child_profile_by_id(self, profile_id: str, user_id: str) -> Optional[ChildProfileModel]:
        """Get a specific child profile (verify ownership)"""
        with get_db() as db:
            profile = db.query(ChildProfile).filter(
                ChildProfile.id == profile_id,
                ChildProfile.user_id == user_id
            ).first()
            
            return ChildProfileModel.model_validate(profile) if profile else None

    def update_child_profile_by_id(
        self, profile_id: str, user_id: str, updated: ChildProfileForm
    ) -> Optional[ChildProfileModel]:
        """Update a child profile (verify ownership)"""
        with get_db() as db:
            profile = db.query(ChildProfile).filter(
                ChildProfile.id == profile_id,
                ChildProfile.user_id == user_id
            ).first()
            
            if profile:
                ts = int(time.time_ns())
                profile.name = updated.name
                profile.child_age = updated.child_age
                profile.child_gender = updated.child_gender
                profile.child_characteristics = updated.child_characteristics
                profile.parenting_style = updated.parenting_style
                profile.updated_at = ts
                
                db.commit()
                db.refresh(profile)
                return ChildProfileModel.model_validate(profile)
            
            return None

    def delete_child_profile(self, profile_id: str, user_id: str) -> bool:
        """Delete a child profile (verify ownership)"""
        with get_db() as db:
            profile = db.query(ChildProfile).filter(
                ChildProfile.id == profile_id,
                ChildProfile.user_id == user_id
            ).first()
            
            if profile:
                db.delete(profile)
                db.commit()
                return True
            return False

    def get_child_profile_stats(self) -> dict:
        """Get statistics about child profiles for analytics"""
        with get_db() as db:
            total_profiles = db.query(ChildProfile).count()
            unique_parents = db.query(ChildProfile.user_id).distinct().count()
            
            return {
                "total_profiles": total_profiles,
                "unique_parents": unique_parents,
            }

# Global instance
ChildProfiles = ChildProfileTable()
