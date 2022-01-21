#
# foris-controller-openvpn_client-module
# Copyright (C) 2019-2020, 2022 CZ.NIC, z.s.p.o. (http://www.nic.cz/)
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

import json
import logging
import pathlib
import typing

from foris_controller_backends.cmdline import BaseCmdLine
from foris_controller_backends.files import BaseFile, makedirs
from foris_controller_backends.maintain import MaintainCommands
from foris_controller_backends.services import OpenwrtServices
from foris_controller_backends.uci import (
    UciBackend,
    get_sections_by_type,
    parse_bool,
    store_bool,
)

logger = logging.getLogger(__name__)

IF_NAME_LEN = 10  # Interface name has to be less then 14 characters and is always prefixed with 'vpn'


class OpenVpnUbus(BaseCmdLine):
    def openvpn_running_instances(self) -> typing.Set[str]:
        """ returns dict with instance name and bool which indicates whether
            the instance is running
        """

        output, _ = self._run_command_and_check_retval(
            ["/bin/ubus", "call", "service", "list", '{"name": "openvpn"}'], 0
        )

        services = json.loads(output)
        if "openvpn" not in services or "instances" not in services["openvpn"]:
            return {}

        return {k for k, v in services["openvpn"]["instances"].items() if v.get("running")}


class OpenVpnClientUci:
    def list(self) -> typing.List[dict]:

        with UciBackend() as backend:
            data = backend.read("openvpn")

        running_instances = OpenVpnUbus().openvpn_running_instances()
        logger.debug("Running openvpn instances %s", running_instances)

        return [
            {
                "id": e["name"],
                "enabled": parse_bool(e["data"].get("enabled", "0")),
                "running": e["name"] in running_instances,
            }
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
            # Do not activate vpn config right after adding it
            # It could mess up already running vpn connections
            # or make router inaccessible in certain circumstances
            # It would be safer to activate vpn connection in separate action later
            backend.set_option("openvpn", id, "enabled", store_bool(False))
            backend.set_option("openvpn", id, "_client_foris", store_bool(True))
            backend.set_option("openvpn", id, "config", str(file_path))
            backend.set_option("openvpn", id, "dev", f"vpn{id[:IF_NAME_LEN]}")
            backend.add_to_list("firewall", "turris_vpn_client", "device", [f"vpn{id[:IF_NAME_LEN]}"])

        self.restart_openvpn()

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
            backend.del_from_list("firewall", "turris_vpn_client", "device", [f"vpn{id[:IF_NAME_LEN]}"])

            file_path = pathlib.Path("/etc/openvpn/foris") / f"{id}.conf"
            BaseFile().delete_file(str(file_path))

        self.restart_openvpn()

        return True

    @staticmethod
    def restart_openvpn():
        """ Restart or reload network interfaces, openvpn itself and firewall rules.
            To make sure that as openvpn works as expected after reconfiguration.
        """
        with OpenwrtServices() as services:
            MaintainCommands().restart_network()
            services.restart("openvpn", delay=3)
            # force firewall reload as it doesn't always get triggered by network restart
            services.reload("firewall", delay=3)
