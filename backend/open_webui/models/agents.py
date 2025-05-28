from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Agent(Base):
    __tablename__ = "agent"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    role = Column(String, nullable=False)
    system_message = Column(String, nullable=True)
    model_id = Column(String, ForeignKey("model.id"), nullable=False) # Changed from llm_model to model_id and added ForeignKey
    skills = Column(JSON, nullable=True)
    user_id = Column(String, ForeignKey("user.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Define the relationship to the User model if User model exists and is defined with Base
    # Assuming User model is in a file named 'users.py' and User class is named 'User'
    # from .users import User  # Import User model
    # owner = relationship("User") # Example relationship
    # model = relationship("Model") # Add relationship to Model table

    def __repr__(self):
        return f"<Agent(id={self.id}, name='{self.name}', user_id='{self.user_id}', model_id='{self.model_id}')>"
