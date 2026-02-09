"""
Domain Layer: Entities and Value Objects
Pure Python, No external dependencies.
"""
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum, auto
from typing import List, Optional, NewType

# --- Value Objects ---

CollectionId = NewType("CollectionId", str)
NFTId = NewType("NFTId", str)

@dataclass(frozen=True)
class Money:
    """Immutable Money Value Object"""
    amount: Decimal
    currency: str = "TON"

    def __lt__(self, other: "Money") -> bool:
        if self.currency != other.currency:
            raise ValueError("Currencies do not match")
        return self.amount < other.amount

    def __le__(self, other: "Money") -> bool:
        if self.currency != other.currency:
            raise ValueError("Currencies do not match")
        return self.amount <= other.amount
    
    def __sub__(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise ValueError("Currencies do not match")
        return Money(self.amount - other.amount, self.currency)

    def __mul__(self, other: float | Decimal) -> "Money":
        val = Decimal(other)
        return Money(self.amount * val, self.currency)

    def __truediv__(self, other: "Money | float | Decimal") -> "Money | float":
        if isinstance(other, Money):
            if self.currency != other.currency:
                raise ValueError("Currencies do not match")
            return float(self.amount / other.amount)
        val = Decimal(other)
        return Money(self.amount / val, self.currency)

# --- Entities ---

class TradingMode(Enum):
    SNIPE = auto()
    MONITOR = auto()

@dataclass
class NFTAttribute:
    """NFT Attribute (Trait)"""
    trait_type: str
    value: str

@dataclass
class NFT:
    """NFT Entity"""
    id: NFTId
    collection_id: CollectionId
    name: str
    rank: Optional[int]
    image_url: str
    price: Money
    attributes: List[NFTAttribute] = field(default_factory=list)
    model: str = "Unknown"

    @property
    def price_val(self) -> float:
        return float(self.price.amount)

@dataclass
class Collection:
    """Collection Entity"""
    id: CollectionId
    name: str # Human readable name
    short_name: str # API identifier (slug)
    models: List[str] = field(default_factory=list) # List of models to watch

    def is_target_model(self, model: str) -> bool:
        return model in self.models

# --- Exceptions ---

class DomainError(Exception):
    """Base domain exception"""

class InsufficientFundsError(DomainError):
    """Raised when wallet balance is lower than price"""

class InvalidConfigurationError(DomainError):
    """Raised when config is invalid"""
