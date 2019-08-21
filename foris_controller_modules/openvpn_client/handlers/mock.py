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

from foris_controller.handler_base import BaseMockHandler
from foris_controller.utils import logger_wrapper

from .. import Handler

logger = logging.getLogger(__name__)


class MockOpenVpnClientHandler(Handler, BaseMockHandler):
    clients = {}

    @logger_wrapper(logger)
    def list(self):
        return [
            {"id": k, "enabled": v["enabled"]} for k, v in MockOpenVpnClientHandler.clients.items()
        ]

    @logger_wrapper(logger)
    def set(self, id, enabled):

        if id not in MockOpenVpnClientHandler.clients:
            return False

        MockOpenVpnClientHandler.clients[id]["enabled"] = enabled
        return True

    @logger_wrapper(logger)
    def add(self, id, config):

        if id in MockOpenVpnClientHandler.clients:
            return False

        MockOpenVpnClientHandler.clients[id] = {"enabled": True, "config": config}
        return True

    @logger_wrapper(logger)
    def delete(self, id):

        if id not in MockOpenVpnClientHandler.clients:
            return False

        del MockOpenVpnClientHandler.clients[id]
        return True
