from pydantic import BaseModel

class TransactionInput(BaseModel):
    features: list
