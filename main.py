import datetime
from typing import Dict
from fastapi import FastAPI
from sqlalchemy import create_engine
import uvicorn
from sqlmodel import SQLModel, Session
from starlette.middleware.cors import CORSMiddleware
from starlette.status import HTTP_200_OK
from starlette.websockets import WebSocket, WebSocketDisconnect

from models import AuctionItem

app = FastAPI()
eng = 'database.db'
sql_url = f'sqlite:///{eng}'
engine = create_engine(sql_url)
session = Session(bind=engine)

app.add_middleware(CORSMiddleware,
                   allow_origins=['http://localhost:8080', 'http://localhost:3000',
                                  'http://localhost:55753'],
                   allow_methods=['*'],
                   allow_headers=['*']
                   )


class AuctionConnectionManager:
    def __init__(self):
        self.auction_connections: Dict[any, list] = {}

    async def connect(self, websocket: WebSocket, auction_id):
        await websocket.accept()
        item_found = session.get(AuctionItem, auction_id)
        print(item_found)
        if (item_found.ends and item_found.ends < datetime.datetime.now()) \
                or item_found.completed:
            item_found.completed = True
            await self.send_personal_message("The auction is already finished!",
                                         websocket)
            await self.send_personal_message(f"{item_found.item_name} was sold for {item_found.bid}"
                                             f" to a bidder #{item_found.bidder_id}!",
                                             websocket)
            await self.send_personal_message(message="", websocket=websocket,
                                             json_data={'completed': True})
            session.commit()
            return
        cur_bid = item_found.bid

        if cur_bid:
            await self.send_personal_message("The auction has already started!",
                                             websocket, cur_bid)
        if not self.auction_connections.get(auction_id):
            self.auction_connections[auction_id] = []
        self.auction_connections[auction_id].append(websocket)

    async def disconnect(self, websocket: WebSocket, auction_id):
        self.auction_connections[auction_id].remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket,
                                    cur_price=None, json_data=None):
        await websocket.send_text(message)
        if cur_price:
            await websocket.send_json({'new_price': cur_price})
        if json_data:
            print(json_data)
            await websocket.send_json({'json_data': json_data})

    async def broadcast(self, message: str, auction_id: int, new_price=None, ends=None):
        for connection in self.auction_connections.get(auction_id):
            await connection.send_text(message)
            payload = {}
            if new_price:
                payload = {'new_price': new_price}
            if ends:
                payload.update(ends=str(ends))
            if payload.keys():
                await connection.send_json(payload)


manager = AuctionConnectionManager()


@app.get('/auction/{id}', status_code=HTTP_200_OK)
async def auction(id: int):
    auction_item = session.get(AuctionItem, id)
    return {'item': auction_item}


@app.websocket('/auction/{id}/ws/{participant_id}')
async def auction(websocket: WebSocket, id: int, participant_id: int):
    await manager.connect(websocket, id)
    try:
        while True:
            data = await websocket.receive_json()
            item = session.get(AuctionItem, id)
            step = item.price_step | 0
            current_bid = item.bid or 0
            min_new_bid = current_bid + step
            new_bid = data.get('bid')

            if not new_bid:
                print(1)
                continue
            if participant_id == item.bidder_id or not new_bid > current_bid:
                print(2)
                continue
            if item.min_price < new_bid >= min_new_bid:
                print(new_bid)
                item.bid = new_bid
                item.bidder_id = participant_id
                item.ends = datetime.datetime.now() + datetime.timedelta(seconds=60)
                await manager.broadcast(f"Participant {participant_id} has bid {item.bid}!", auction_id=id, new_price=item.bid,
                                        ends=item.ends)
                session.commit()

    except WebSocketDisconnect:
        await manager.disconnect(websocket, id)
        await manager.broadcast(f"Participant has left the auction", auction_id=id)


if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)
    #SQLModel.metadata.create_all(engine)