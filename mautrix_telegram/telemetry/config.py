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

from typing import TYPE_CHECKING, Union, cast
import logging

from attr import dataclass, field

from mautrix.types import (
    IdentifierType,
    PowerLevelStateEventContent,
    RoomAlias,
    RoomCreatePreset,
    RoomDirectoryVisibility,
    RoomID,
)

if TYPE_CHECKING:
    from attr import Attribute


@dataclass
class Config:
    instance_id: str
    matrix_destination: MatrixDestinationConfig
    http_destination: HTTPDestinationConfig | None


class MatrixDestinationConfig:
    log: logging.Logger = logging.getLogger("mau.telemetry.config")

    room_id_or_alias: RoomIDOrAlias | None = None
    room_creation_options: dict | None = None

    def __init__(
        self,
        room_id_or_alias: RoomID | RoomAlias | None,
        room_creation_options: dict | None,
    ):
        if not room_id_or_alias and room_creation_options is None:
            raise ValueError(
                '"telemetry.matrix_destination" must specify at least one of '
                '"room_id_or_alias" or "room_creation"'
            )

        if room_id_or_alias:
            # TODO: when/if there exists a mautrix helper function to validate a room ID/alias, use it
            self.room_id_or_alias = self.RoomIDOrAlias(room_id_or_alias)

        if room_creation_options is not None:

            def to_plain_dict_recursive(d) -> dict:
                """Deep-convert a ruamel "Commented" object into a plain one."""
                p = {**d}
                for k, v in p.items():
                    if isinstance(v, dict):
                        p[k] = to_plain_dict_recursive(v)
                    elif isinstance(v, list):
                        p[k] = [*v]
                return p

            self.room_creation_options = to_plain_dict_recursive(room_creation_options)
            self._convert_room_creation_options(self.room_creation_options)

    class RoomIDOrAlias:
        localpart: str
        domain: str

        _value: RoomID | RoomAlias
        is_room_id: bool

        def __init__(self, s: str):
            try:
                id_type = IdentifierType(s[0])
                if id_type == IdentifierType.ROOM_ID:
                    self.is_room_id = True
                elif id_type == IdentifierType.ROOM_ALIAS:
                    self.is_room_id = False
                else:
                    raise KeyError()
                self.localpart, self.domain = s[1:].split(":", 1)
                self._value = cast(Union[RoomID, RoomAlias], s)
            except:
                raise ValueError(f'"{s}" is not a valid room ID or alias')

        @property
        def is_room_alias(self) -> bool:
            return not self.is_room_id

        def get(self) -> RoomID | RoomAlias:
            return self._value

        __str__ = get

    def _convert_room_creation_options(self, room_creation_options: dict) -> None:
        """
        Convert a room creation options object for the CS API's "createRoom" endpoint
        into a kwargs object compatible with mautrix-python's "RoomMethods.create_room".
        """
        if room_creation_options.pop("room_alias_name", None):
            self.log.warning(
                'Ignoring "room_alias_name" in the telemetry room creation config object. '
                "To specify the alias of the telemetry room to join/create, "
                'set "telemetry.matrix_destination.room_id_or_alias" instead.'
            )
        try:
            room_creation_options["visibility"] = RoomDirectoryVisibility(
                room_creation_options.pop("visibility")
            )
        except KeyError:
            pass
        try:
            room_creation_options["preset"] = RoomCreatePreset(room_creation_options.pop("preset"))
        except KeyError:
            pass
        try:
            room_creation_options["invitees"] = room_creation_options.pop("invite")
        except KeyError:
            pass
        try:
            room_creation_options["power_level_override"] = PowerLevelStateEventContent(
                **room_creation_options.pop("power_level_content_override")
            )
        except KeyError:
            pass


@dataclass
class HTTPDestinationConfig:
    num_attempts: int = field(converter=int)
    retry_delay: float = field(converter=float)
    submission_url: str

    @num_attempts.validator
    def _check_num_attempts(self, attribute: Attribute, value: int) -> None:
        if value <= 0:
            raise ValueError(f"{attribute.name} must be a positive integer")

    @retry_delay.validator
    def _check_retry_delay(self, attribute: Attribute, value: float) -> None:
        if value < 0:
            raise ValueError(f"{attribute.name} must be non-negative")
