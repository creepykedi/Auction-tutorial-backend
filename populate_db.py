from sqlmodel import Session
from main import engine
from models import AuctionItem
import random


def create_auct_item():
    r = random.randint(1,100)
    item_name = f'Painting number {r}'
    item_description = f'Description for painting number {r}'
    min_price = random.randint(5000,20000)
    price_step = min_price/10
    return AuctionItem(item_name=item_name, item_description=item_description,
                       min_price=min_price, price_step=price_step)


def create_auct_db():
    items = [create_auct_item() for _ in range(10)]
    with Session(engine) as session:
        session.add_all(items)
        session.commit()

create_auct_db()