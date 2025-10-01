from datetime import datetime, timezone
import enum
from typing import List, Optional
from sqlalchemy import Column, DateTime, Integer, String
from sqlmodel import Relationship, SQLModel, Field

from app.core.config import get_data_dir

class Category(str, enum.Enum):
  PRODUTIVO = "Produtivo"
  IMPRODUTIVO = "Improdutivo"
  SEM_CLASSIFICACAO = "Sem classificação"

class Status(str, enum.Enum):
  PROCESSING = "Processando"
  COMPLETED = "Concluído"
  FAILED = "Falhou"
class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str
    email: str
    hash_password: str
    created_at: datetime = Field(
      default_factory=lambda: datetime.now(timezone.utc),
      sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    texts: List["TextEntry"] = Relationship(back_populates="user")
        
class TextEntry(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    original_text: str
    category: Optional[Category] = Field(default=None, sa_column=Column(String, nullable=True))
    generated_response: Optional[str] = Field(default="", sa_column=Column(String, nullable=True))
    status: Status = Field(default=Status.PROCESSING, sa_column=Column(String, default=Status.PROCESSING.value))

    file_name: str = Field(default=None, sa_column=Column(String))
    file_path: str = Field(default=str(get_data_dir()), sa_column=Column(String))
    file_content_type: Optional[str] = Field(default=None, sa_column=Column(String))
    file_size: Optional[int] = Field(default=None, sa_column=Column(Integer))

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    user: User = Relationship(back_populates="texts")
    