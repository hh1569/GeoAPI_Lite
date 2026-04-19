from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class UserCreate(BaseModel):
    name: str
    password: str
    phone: str

class UserDetail(BaseModel):
    userid: int
    name: str
    phone: str
    update_time: datetime
    model_config = ConfigDict(
            from_attributes=True,  # 允许从ORM对象属性取值
        )

class UserUpdate(BaseModel):
    name: str
    phone: str


