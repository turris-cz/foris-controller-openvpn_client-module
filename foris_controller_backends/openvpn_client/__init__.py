#
# foris-controller-openvpn_client-module
# Copyright (C) 2019 CZ.NIC, z.s.p.o. (http://www.nic.cz/)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301  USA
#

import logging
import pathlib
import random
import typing

from foris_controller_backends.cmdline import BaseCmdLine
from foris_controller_backends.files import makedirs, BaseFile
from foris_controller_backends.maintain import MaintainCommands
from foris_controller_backends.services import OpenwrtServices
from foris_controller_backends.uci import (
    UciBackend,
    get_option_named,
    get_sections_by_type,
    parse_bool,
    store_bool,
)

logger = logging.getLogger(__name__)


class OpenVpnClientUci:
    def list(self) -> typing.List[dict]:

        with UciBackend() as backend:
            data = backend.read("openvpn")

        return [
            {"id": e["name"], "enabled": parse_bool(e["data"].get("enabled", "0"))}
            for e in get_sections_by_type(data, "openvpn", "openvpn")
            if parse_bool(e["data"].get("_client_foris", "0"))
        ]

    def add(self, id: str, config: str) -> bool:

        with UciBackend() as backend:
            data = backend.read("openvpn")

            # try if it exists
            existing_ids = [e["name"] for e in get_sections_by_type(data, "openvpn", "openvpn")]
            if id in existing_ids:
                return False

            # write config file
            dir_path = pathlib.Path("/etc/openvpn/foris")
            file_path = dir_path / f"{id}.conf"
            makedirs(str(dir_path), mask=0o0700)
            BaseFile()._store_to_file(str(file_path), config)

            # update uci
            backend.add_section("openvpn", "openvpn", id)
            backend.set_option("openvpn", id, "enabled", store_bool(True))
            backend.set_option("openvpn", id, "_client_foris", store_bool(True))
            backend.set_option("openvpn", id, "config", str(file_path))

        with OpenwrtServices() as services:
            MaintainCommands().restart_network()
            services.restart("openvpn", delay=3)

        return True

    def set(self, id: str, enabled: bool) -> bool:

        with UciBackend() as backend:
            data = backend.read("openvpn")

            # try if it exists
            existing_ids = [e["name"] for e in get_sections_by_type(data, "openvpn", "openvpn")]
            if id not in existing_ids:
                return False

            # update uci
            backend.add_section("openvpn", "openvpn", id)
            backend.set_option("openvpn", id, "enabled", store_bool(enabled))

        with OpenwrtServices() as services:
            MaintainCommands().restart_network()
            services.restart("openvpn", delay=3)

        return True

    def delete(self, id: str) -> bool:

        with UciBackend() as backend:
            data = backend.read("openvpn")

            # try if it exists
            existing_ids = [e["name"] for e in get_sections_by_type(data, "openvpn", "openvpn")]
            if id not in existing_ids:
                return False

            backend.del_section("openvpn", id)

            file_path = pathlib.Path("/etc/openvpn/foris") / f"{id}.conf"
            BaseFile().delete_file(str(file_path))

        with OpenwrtServices() as services:
            MaintainCommands().restart_network()
            services.restart("openvpn", delay=3)

        return True
