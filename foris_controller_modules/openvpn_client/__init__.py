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

from foris_controller.module_base import BaseModule
from foris_controller.handler_base import wrap_required_functions
from foris_controller_openvpn_client_module.utils import sanitize_id


class OpenVpnClientModule(BaseModule):
    logger = logging.getLogger(__name__)

    def action_list(self, data: dict):
        return {"clients": self.handler.list()}

    def action_add(self, data: dict):
        data["id"] = sanitize_id(data["id"])
        res = self.handler.add(**data)
        if res:
            self.notify("add", {"id": data["id"]})
        return {"result": res}

    def action_set(self, data: dict):
        res = self.handler.set(**data)
        if res:
            self.notify("set", data)
        return {"result": res}

    def action_del(self, data: dict):
        res = self.handler.delete(**data)
        if res:
            self.notify("del", {"id": data["id"]})
        return {"result": res}


@wrap_required_functions(["list", "add", "delete", "set"])
class Handler(object):
    pass
