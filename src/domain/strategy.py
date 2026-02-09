"""
Domain Layer: Sniper Strategy
Contains pure business logic for purchase decisions.
"""
from decimal import Decimal
from typing import Optional

from .models import NFT, Money, InsufficientFundsError

class ProfitCalculator:
    """Calculates potential profit based on floor price and fees"""
    
    def __init__(self, market_fee: float = 0.05):
        self.market_fee = Decimal(str(market_fee))

    def calculate_net_profit(self, buy_price: Money, floor_price: Money) -> Money:
        """
        Profit = (Floor * (1 - Fee)) - BuyPrice
        """
        if buy_price.currency != floor_price.currency:
            raise ValueError("Currency mismatch")

        # Sell price is the floor price
        sell_price_after_fee = floor_price.amount * (Decimal("1.0") - self.market_fee)
        profit_amount = sell_price_after_fee - buy_price.amount
        
        return Money(profit_amount, buy_price.currency)


class SnipeStrategy:
    """Decides if an NFT should be bought"""
    
    def __init__(self, min_profit: Money):
        self.min_profit = min_profit

    def should_buy(self, nft: NFT, floor_price: Money, balance: Money) -> bool:
        """
        Determines if we should buy the NFT.
        Rules:
        1. Balance >= Price
        2. Profit >= MinProfit
        """
        # 1. Check Balance
        if balance < nft.price:
            return False

        # 2. Check Profit
        # We assume we can instantly sell at floor price
        calculator = ProfitCalculator() # using default fee (or could be injected)
        projected_profit = calculator.calculate_net_profit(nft.price, floor_price)

        if projected_profit.amount >= self.min_profit.amount:
            return True
        
        return False
