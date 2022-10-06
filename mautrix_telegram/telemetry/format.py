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
"""Helpers to convert telemetry payloads into human-readable formats."""

from typing import List

from attr import asdict, fields, filters

from .types import Telemetry


def _get_metadata_rows(telemetry: Telemetry) -> List[str]:
    return [
        f"{prop}: {value}"
        for prop, value in asdict(
            telemetry,
            filter=filters.exclude(
                fields(Telemetry).generationTime,
                fields(Telemetry).data,
            ),
        ).items()
    ]


def telemetry_to_html(telemetry: Telemetry) -> str:
    return "\n".join(
        [
            "<h1>Metadata</h1>",
            "<ul>",
        ]
        + [f"  <li>{row}</li>" for row in _get_metadata_rows(telemetry)]
        + [
            "</ul>",
            "<h1>Data</h1>",
            "<ul>",
            f"  <li>rmau.allUsers: {telemetry.data.rmau.allUsers}</li>",
            "</ul>",
        ]
    )


def telemetry_to_markdown(telemetry: Telemetry) -> str:
    return "\n".join(
        [
            "# Metadata",
            "",
        ]
        + [f"- {row}" for row in _get_metadata_rows(telemetry)]
        + [
            "",
            "# Data",
            "",
            f"- rmau.allUsers: {telemetry.data.rmau.allUsers}",
            "",
        ]
    )
