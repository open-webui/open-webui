from pydantic import BaseModel
from peewee import *
from playhouse.shortcuts import model_to_dict
from typing import List, Union, Optional
import logging

from apps.web.internal.db import MSSQL_DB
from config import MSSQL_VIEW

from sqlalchemy import create_engine, Column, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

####################
# Staff DB Schema
####################


class Staff(Base):
    __tablename__ = MSSQL_VIEW
    emp_id = Column(name='EmpId', type_=String, primary_key=True)
    email = Column(name='Email', type_=String, unique=True)
    emp_type = Column(name='EmpType', type_=String)
    first_name = Column(name='FirstName', type_=String)
    last_name = Column(name='LastName', type_=String)
    job_title = Column(name='JobTitle', type_=String)
    department = Column(name='Department', type_=String)
    new_department = Column(name='NewDepartment', type_=String)
    line_manager_name = Column(name='LineManagername', type_=String)
    line_manager_email = Column(name='LineManagerEmail', type_=String)

class StaffsTable:
    def __init__(self, db):
        self.db = db

    def get_staff_by_email(self, email: str) -> Optional[Staff]:
        try:
            self.db.create_all()
            staff = self.db.query(Staff).filter(Staff.email == email).first()
            self.db.close()
            return staff
        except Exception as e:
            logging.error(f"Error getting staff by email: {email}. Exception: {e}")
            return None


Staffs = StaffsTable(MSSQL_DB)
