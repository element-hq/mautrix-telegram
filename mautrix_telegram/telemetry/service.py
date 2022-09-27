# mautrix-telegram - A Matrix-Telegram puppeting bridge
# Copyright (C) 2021 Tulir Asokan
# Copyright (C) 2022 New Vector Ltd
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
from __future__ import annotations

from typing import TYPE_CHECKING
import asyncio
import logging
import time

from aiohttp import BasicAuth, ClientSession, hdrs
from attr import dataclass

from mautrix.api import HTTPAPI
from mautrix.client import ClientAPI
from mautrix.errors import MatrixRequestError, MExclusive, MNotFound
from mautrix.types import (
    EventType,
    Format,
    MessageType,
    RoomCreateStateEventContent,
    RoomID,
    RoomType,
    SerializableAttrs,
    SerializerError,
    TextMessageEventContent,
)

from .config import Config, HTTPDestinationConfig, MatrixDestinationConfig
from .format import telemetry_to_html, telemetry_to_markdown
from .types import Telemetry as TelemetryEventContent, TelemetryData, TelemetryDataRMAU

if TYPE_CHECKING:
    from ..__main__ import TelegramBridge


TelemetryEventType = EventType.find("io.element.ems.telemetry", EventType.Class.MESSAGE)

TelemetryRoomEventType = EventType.find(
    f"{TelemetryEventType.t}.storage.room", EventType.Class.ACCOUNT_DATA
)


@dataclass
class TelemetryRoomEventContent(SerializableAttrs):
    room_id: RoomID


RoomType.TELEMETRY_ROOM = TelemetryRoomEventType.t
# NOTE: redefining as a global to satisfy static type checks
TelemetryRoomType: RoomType = RoomType.TELEMETRY_ROOM


class TelemetryService:
    log: logging.Logger = logging.getLogger("mau.telemetry.service")

    _hostname: str
    _matrix_client: ClientAPI

    _config: Config

    _session: ClientSession | None = None

    def __init__(self, bridge: TelegramBridge, instance_id: str) -> None:
        if not bridge.config["telemetry.enabled"]:
            raise ValueError(
                "TelemetryService cannot be initialized if telemetry is not configured"
            )

        self._hostname = bridge.az.domain
        self._matrix_client = bridge.az.intent

        self._config = Config(
            instance_id,
            MatrixDestinationConfig(
                bridge.config["telemetry.matrix_destination.room_id_or_alias"],
                bridge.config["telemetry.matrix_destination.room_creation.options"]
                if bridge.config["telemetry.matrix_destination.room_creation.enabled"]
                else None,
            ),
            HTTPDestinationConfig(
                bridge.config["telemetry.http_destination.num_attempts"],
                bridge.config["telemetry.http_destination.retry_delay"],
                bridge.config["telemetry.http_destination.submission_url"],
            )
            if bridge.config["telemetry.http_destination.enabled"]
            else None,
        )
        if self._config.matrix_destination.room_creation_options is not None:
            if self._config.matrix_destination.room_id_or_alias and (
                self._config.matrix_destination.room_id_or_alias.is_room_id
                or self._config.matrix_destination.room_id_or_alias.domain != self._hostname
            ):
                raise ValueError(
                    '"telemetry.matrix_destination.room_id_or_alias" must refer to a local room alias when '
                    '"telemetry.matrix_destination.room_creation" is set'
                )

        if self._config.http_destination:
            # NOTE: not storing credentials in a config class as they get stored in the ClientSession
            self._session = ClientSession(
                loop=bridge.loop,
                headers={
                    hdrs.USER_AGENT: HTTPAPI.default_ua,
                    hdrs.CONTENT_TYPE: "application/json",
                },
                auth=BasicAuth(
                    bridge.config["telemetry.http_destination.credentials.username"],
                    bridge.config["telemetry.http_destination.credentials.password"],
                ),
            )

    async def _load_storage_room(self) -> RoomID:
        remembered_room_id = None
        try:
            remembered_room_id = TelemetryRoomEventContent.deserialize(
                await self._matrix_client.get_account_data(TelemetryRoomEventType)
            ).room_id
        except (MNotFound, SerializerError):
            pass
        except:
            self.log.exception("Failed to retrieve previously-used telemetry room")

        room_id = None
        if self._config.matrix_destination.room_id_or_alias:
            try:
                room_id = await self._matrix_client.join_room(
                    self._config.matrix_destination.room_id_or_alias.get(),
                    max_retries=0,
                )
            except MNotFound:
                if self._config.matrix_destination.room_id_or_alias.is_room_id:
                    raise
        elif remembered_room_id:
            try:
                room_id = await self._matrix_client.join_room_by_id(remembered_room_id)
            except Exception as e:
                self.log.error(
                    f"Could not join previously-used telemetry room {remembered_room_id}: {e}"
                )

        if not room_id:
            if self._config.matrix_destination.room_creation_options is None:
                raise Exception("Telemetry room creation blocked by config")

            if (
                self._config.matrix_destination.room_id_or_alias
                and self._config.matrix_destination.room_id_or_alias.is_room_alias
            ):
                alias_localpart = self._config.matrix_destination.room_id_or_alias.localpart
            else:
                alias_localpart = None
            try:
                room_id = await self._matrix_client.create_room(
                    alias_localpart,
                    creation_content=RoomCreateStateEventContent(type=TelemetryRoomType),
                    **(self._config.matrix_destination.room_creation_options),
                )
            except MExclusive as e:
                raise RuntimeError(
                    "Failed to create telemetry room with alias "
                    f'#{alias_localpart}:{self._hostname}". '
                    "To grant the bridge permission to use this alias, "
                    "regenerate the bridge registration file."
                ) from None

        if remembered_room_id and remembered_room_id != room_id:
            try:
                await self._matrix_client.leave_room(remembered_room_id)
            except MatrixRequestError:
                pass
            except:
                self.log.exception("Failed to leave previously-used telemetry room")
        try:
            await self._matrix_client.set_account_data(
                TelemetryRoomEventType, TelemetryRoomEventContent(room_id).serialize()
            )
        except:
            self.log.exception("Failed to store telemetry room")
        return room_id

    async def send_telemetry(
        self, active_users: int, current_ms: float = time.time() * 1000
    ) -> None:
        telemetry = TelemetryEventContent(
            instanceId=self._config.instance_id,
            hostname=self._hostname,
            generationTime=int(current_ms),
            data=TelemetryData(
                rmau=TelemetryDataRMAU(
                    allUsers=active_users,
                ),
            ),
        )
        telemetry_json = telemetry.serialize()
        self.log.debug(f"Sending telemetry: {telemetry_json}")

        try:
            room_id = await self._load_storage_room()
            human_readable_event_data = TextMessageEventContent(
                body=telemetry_to_markdown(telemetry),
                format=Format.HTML,
                formatted_body=telemetry_to_html(telemetry),
                msgtype=MessageType.TEXT,
            )
            content = human_readable_event_data.serialize()
            content[TelemetryEventType.t] = telemetry_json
            await self._matrix_client.send_message(room_id, content)
        except:
            self.log.exception("Failed to record telemetry in Matrix")

        if self._config.http_destination:
            assert self._session
            attempts_left = self._config.http_destination.num_attempts
            while True:
                try:
                    request = self._session.request(
                        hdrs.METH_POST,
                        self._config.http_destination.submission_url,
                        json=telemetry_json,
                    )
                    async with request as response:
                        response.raise_for_status()
                        break
                except:
                    self.log.exception("Failed to submit telemetry")
                    if attempts_left > 1:
                        self.log.debug(
                            f"Will retry sending telemetry in {self._config.http_destination.retry_delay} seconds"
                        )
                        attempts_left -= 1
                        await asyncio.sleep(self._config.http_destination.retry_delay)
                    else:
                        break
