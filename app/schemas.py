from datetime import datetime
from pydantic import BaseModel, ConfigDict

class UserCreateRequest(BaseModel):
    username: str
    email: str
    password: str
    
class UserLoginRequest(BaseModel):
    email: str
    password: str
    
class UserUpdateRequest(BaseModel):
    username: str | None = None
    email: str | None = None
    current_password: str | None = None
    new_password: str | None = None

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
    original_text: str | None = None
    category: str | None = None
    created_at: datetime
    generated_response: str | None = None
    file_name: str | None = None
    
class TokenResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    access_token: str
    token_type: str = "bearer"
    user_id: int


class ProcessResultResponse(BaseModel):
    category: str
    confidence: float | None = None
    generated_response: str | None = None

class TaskStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    task_id: str
    status: str
    result: ProcessResultResponse | None = None