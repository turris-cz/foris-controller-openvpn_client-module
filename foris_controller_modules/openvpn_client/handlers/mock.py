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

import logging
import typing

from foris_controller.handler_base import BaseMockHandler
from foris_controller.utils import logger_wrapper

from .. import Handler
from ..datatypes import OpenVPNClientCredentials

logger = logging.getLogger(__name__)


class MockOpenVpnClientHandler(Handler, BaseMockHandler):
    clients = {}

    @logger_wrapper(logger)
    def list(self):
        return [
            {
                "id": k,
                "enabled": v["enabled"],
                "running": False,
                "credentials": {
                    "username": v.get("username", ""),
                    "password": v.get("password", ""),
                }
            }
            for k, v in MockOpenVpnClientHandler.clients.items()
        ]

    @logger_wrapper(logger)
    def set(self, id, enabled, credentials: typing.Optional[OpenVPNClientCredentials] = None):

        if id not in MockOpenVpnClientHandler.clients:
            return False

        MockOpenVpnClientHandler.clients[id]["enabled"] = enabled
        MockOpenVpnClientHandler._set_client_credentials(id, credentials)

        return True

    @logger_wrapper(logger)
    def add(self, id, config, credentials: typing.Optional[OpenVPNClientCredentials] = None):

        if id in MockOpenVpnClientHandler.clients:
            return False

        MockOpenVpnClientHandler.clients[id] = {"enabled": False, "config": config}
        MockOpenVpnClientHandler._set_client_credentials(id, credentials)

        return True

    @logger_wrapper(logger)
    def delete(self, id):

        if id not in MockOpenVpnClientHandler.clients:
            return False

        del MockOpenVpnClientHandler.clients[id]
        return True

    @staticmethod
    @logger_wrapper(logger)
    def _set_client_credentials(id: str, credentials: typing.Optional[OpenVPNClientCredentials] = None) -> None:
        if credentials is not None:
            username = credentials.get("username")
            password = credentials.get("password")
            if username is not None and password is not None:
                MockOpenVpnClientHandler.clients[id]["username"] = username
                MockOpenVpnClientHandler.clients[id]["password"] = password
