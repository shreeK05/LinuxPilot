import uuid
from typing import Any
from sqlalchemy.orm import as_declarative, declared_attr
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import UUID

@as_declarative()
class Base:
    id: Any
    __name__: str
    
    # Generate __tablename__ automatically
    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower()

def generate_uuid():
    return str(uuid.uuid4())
