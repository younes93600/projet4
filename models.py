from pydantic import BaseModel
from typing import List, Optional

class ProductBase(BaseModel):
    nom: str
    prix: float
    quantite: int

class ProductCreate(ProductBase):
    pass

class Product(ProductBase):
    id: int

    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class OrderItem(BaseModel):
    id: int
    qte: int

class OrderCreate(BaseModel):
    client: Optional[str] = "Client Anonyme"
    items: List[OrderItem]

class OrderResponse(BaseModel):
    success: bool
    message: str
    transaction_id: Optional[str] = None
