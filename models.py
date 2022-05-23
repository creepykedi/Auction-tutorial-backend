import datetime
from typing import Optional

from sqlmodel import SQLModel, Field


class AuctionItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    bidder_id: Optional[int]
    item_name: str
    item_description: Optional[str]
    bid: Optional[float]
    min_price: float = 0
    price_step: Optional[int]
    completed: bool = False
    start: datetime.datetime = datetime.datetime.now()
    ends: Optional[datetime.datetime]