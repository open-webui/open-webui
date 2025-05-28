from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from open_webui.models.agents import Agent as AgentModel
from open_webui.models.auths import User as UserModel
from open_webui.utils.utils import get_current_user, get_db
from pydantic import BaseModel, Field
from datetime import datetime

router = APIRouter()

# Pydantic Schemas for Agent CRUD operations

class AgentBase(BaseModel):
    name: str
    role: str
    system_message: Optional[str] = None
    model_id: str # Changed from llm_model to model_id
    skills: Optional[List[str]] = None # Assuming skills are a list of strings for now

class AgentCreate(AgentBase):
    pass

class AgentResponse(AgentBase):
    id: int
    user_id: str
    timestamp: datetime

    class Config:
        orm_mode = True # For FastAPI to map SQLAlchemy models to Pydantic models

# API Endpoints

@router.post("/", response_model=AgentResponse)
async def create_agent(agent_data: AgentCreate, db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    agent = AgentModel(**agent_data.model_dump(), user_id=current_user.id)
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent

@router.get("/", response_model=List[AgentResponse])
async def get_agents(db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    agents = db.query(AgentModel).filter(AgentModel.user_id == current_user.id).all()
    return agents

@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: int, db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    agent = db.query(AgentModel).filter(AgentModel.id == agent_id, AgentModel.user_id == current_user.id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent

@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(agent_id: int, agent_data: AgentCreate, db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    agent = db.query(AgentModel).filter(AgentModel.id == agent_id, AgentModel.user_id == current_user.id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    for key, value in agent_data.model_dump(exclude_unset=True).items():
        setattr(agent, key, value)
    
    agent.timestamp = datetime.utcnow() # Update timestamp
    db.commit()
    db.refresh(agent)
    return agent

@router.delete("/{agent_id}", status_code=204)
async def delete_agent(agent_id: int, db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    agent = db.query(AgentModel).filter(AgentModel.id == agent_id, AgentModel.user_id == current_user.id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    db.delete(agent)
    db.commit()
    return None
