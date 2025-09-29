from datetime import datetime
from pydantic import BaseModel, ConfigDict

class UserCreateRequest(BaseModel):
    username: str
    email: str
    password: str
    
class UserLoginRequest(BaseModel):
    email: str
    password: str
    
class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    username: str
    email: str
    texts: list["TextEntryResponse"]
    
class TextEntryCreateRequest(BaseModel):
    user_id: int
    original_text: str | None = None
    file_name: str | None = None
    
class TextEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    user_id: int
    status: str
    original_text: str
    category: str
    created_at: datetime
    generated_response: str
    file_name: str | None = None
    
class TokenResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    access_token: str
    token_type: str = "bearer"
    user_id: int


class TaskStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    task_id: str
    status: str