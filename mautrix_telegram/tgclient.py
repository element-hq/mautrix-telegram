# mautrix-telegram - A Matrix-Telegram puppeting bridge
# Copyright (C) 2019 Tulir Asokan
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
from typing import List, Union, Optional, Awaitable

from telethon import TelegramClient, utils
from telethon.tl.functions.messages import SendMediaRequest
from telethon.tl.types import (TypeInputMedia, TypeInputPeer, TypeMessageEntity, TypeMessageMedia,
                               TypePeer)
from telethon.tl.patched import Message
from telethon.sessions.abstract import Session

from .mix.client import MixClient
from .mix import Command


class MautrixTelegramClient(TelegramClient):
    session: Session
    in_bucket: bool
    mix: MixClient
    mxid: str
    target_bucket: int

    async def send_media(self, entity: Union[TypeInputPeer, TypePeer],
                         media: Union[TypeInputMedia, TypeMessageMedia],
                         caption: str = None, entities: List[TypeMessageEntity] = None,
                         reply_to: int = None) -> Optional[Message]:
        entity = await self.get_input_entity(entity)
        reply_to = utils.get_message_id(reply_to)
        request = SendMediaRequest(entity, media, message=caption or "", entities=entities or [],
                                   reply_to_msg_id=reply_to)
        return self._get_response_message(request, await self(request), entity)

    async def __call__(self, request, ordered=False):
        if not self.in_bucket:
            print(f"Proxying {request} through {self.target_bucket}")
            return await self.mix.pickled_call(Command.TELEGRAM_RPC, payload=(self.mxid, request),
                                               target=self.target_bucket)
        else:
            return await super().__call__(request, ordered)

    def connect(self) -> Awaitable[None]:
        if not self.in_bucket:
            raise ValueError("Can't connect() delegated client")
        return super().connect()

    def is_connected(self) -> bool:
        return not self.in_bucket or super().is_connected()
