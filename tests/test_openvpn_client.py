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

import pytest
import pathlib

from foris_controller_testtools.fixtures import (
    network_restart_command,
    init_script_result,
    uci_configs_init,
    only_backends,
    backend,
    infrastructure,
    start_buses,
    mosquitto_test,
    ubusd_test,
    notify_api,
    lock_backend,
    UCI_CONFIG_DIR_PATH,
    FILE_ROOT_PATH,
)

from foris_controller_testtools.utils import (
    sh_was_called,
    network_restart_was_called,
    get_uci_module,
)

from foris_controller.exceptions import UciRecordNotFound


def add(infrastructure, id, config):
    return infrastructure.process_message(
        {
            "module": "openvpn_client",
            "action": "add",
            "kind": "request",
            "data": {"id": id, "config": config},
        }
    )


def set(infrastructure, id, enabled):
    return infrastructure.process_message(
        {
            "module": "openvpn_client",
            "action": "set",
            "kind": "request",
            "data": {"id": id, "enabled": enabled},
        }
    )


def delete(infrastructure, id):
    return infrastructure.process_message(
        {"module": "openvpn_client", "action": "del", "kind": "request", "data": {"id": id}}
    )


def list(infrastructure):
    return infrastructure.process_message(
        {"module": "openvpn_client", "action": "list", "kind": "request"}
    )["data"]["clients"]


def test_list(infrastructure, start_buses):
    res = infrastructure.process_message(
        {"module": "openvpn_client", "action": "list", "kind": "request"}
    )
    assert "error" not in res
    assert "data" in res
    assert "clients" in res["data"]


def test_complext(
    uci_configs_init, init_script_result, infrastructure, start_buses, network_restart_command
):
    filters = [("openvpn_client", "add")]
    notifications = infrastructure.get_notifications(filters=filters)

    # add new
    res = add(infrastructure, "first", "1")
    assert "errors" not in res
    assert res["data"]["result"]
    assert {"id": "first", "enabled": True} in list(infrastructure)

    notifications = infrastructure.get_notifications(notifications, filters=filters)
    assert notifications[-1] == {
        u"module": "openvpn_client",
        u"action": "add",
        u"kind": "notification",
        u"data": {"id": "first"},
    }

    # add existing
    res = add(infrastructure, "first", "2")
    assert "errors" not in res
    assert not res["data"]["result"]
    assert {"id": "first", "enabled": True} in list(infrastructure)

    # set
    filters = [("openvpn_client", "set")]
    notifications = infrastructure.get_notifications(filters=filters)

    res = set(infrastructure, "first", False)
    assert "errors" not in res
    assert res["data"]["result"]
    assert {"id": "first", "enabled": False} in list(infrastructure)

    notifications = infrastructure.get_notifications(notifications, filters=filters)
    assert notifications[-1] == {
        u"module": "openvpn_client",
        u"action": "set",
        u"kind": "notification",
        u"data": {"id": "first", "enabled": False},
    }

    res = set(infrastructure, "first", True)
    assert "errors" not in res
    assert res["data"]["result"]
    assert {"id": "first", "enabled": True} in list(infrastructure)

    notifications = infrastructure.get_notifications(notifications, filters=filters)
    assert notifications[-1] == {
        u"module": "openvpn_client",
        u"action": "set",
        u"kind": "notification",
        u"data": {"id": "first", "enabled": True},
    }

    # set missing
    res = set(infrastructure, "second", False)
    assert "errors" not in res
    assert not res["data"]["result"]
    assert {"id": "first", "enabled": True} in list(infrastructure)

    # del
    filters = [("openvpn_client", "del")]
    notifications = infrastructure.get_notifications(filters=filters)

    res = delete(infrastructure, "first")
    assert "errors" not in res
    assert res["data"]["result"]
    assert "first" not in {e["id"] for e in list(infrastructure)}

    notifications = infrastructure.get_notifications(notifications, filters=filters)
    assert notifications[-1] == {
        u"module": "openvpn_client",
        u"action": "del",
        u"kind": "notification",
        u"data": {"id": "first"},
    }

    # del missing (deleted)
    res = delete(infrastructure, "first")
    assert "errors" not in res
    assert not res["data"]["result"]
    assert "first" not in {e["id"] for e in list(infrastructure)}


@pytest.mark.only_backends(["openwrt"])
def test_complext_openwrt(
    uci_configs_init,
    init_script_result,
    infrastructure,
    start_buses,
    network_restart_command,
    lock_backend,
):
    uci = get_uci_module(lock_backend)

    assert len(list(infrastructure)) == 0

    # add
    res = add(infrastructure, "openwrt_first", "config content")
    assert res["data"]["result"]

    assert network_restart_was_called([])
    assert sh_was_called(["/etc/init.d/openvpn", "restart"])

    with uci.UciBackend(UCI_CONFIG_DIR_PATH) as backend:
        data = backend.read()
    assert uci.parse_bool(uci.get_option_named(data, "openvpn", "openwrt_first", "enabled")) is True
    assert (
        uci.parse_bool(uci.get_option_named(data, "openvpn", "openwrt_first", "_client_foris"))
        is True
    )
    assert (
        uci.get_option_named(data, "openvpn", "openwrt_first", "config")
        == "/etc/openvpn/foris/openwrt_first.conf"
    )

    path = pathlib.Path(FILE_ROOT_PATH) / "etc/openvpn/foris/openwrt_first.conf"

    assert path.exists()
    assert path.read_text() == "config content"

    res = set(infrastructure, "openwrt_first", False)
    assert res["data"]["result"]

    # set
    with uci.UciBackend(UCI_CONFIG_DIR_PATH) as backend:
        data = backend.read()

    assert network_restart_was_called([])
    assert sh_was_called(["/etc/init.d/openvpn", "restart"])

    assert (
        uci.parse_bool(uci.get_option_named(data, "openvpn", "openwrt_first", "enabled")) is False
    )

    # delete
    res = delete(infrastructure, "openwrt_first")
    assert res["data"]["result"]

    assert network_restart_was_called([])
    assert sh_was_called(["/etc/init.d/openvpn", "restart"])

    with uci.UciBackend(UCI_CONFIG_DIR_PATH) as backend:
        data = backend.read()

    with pytest.raises(UciRecordNotFound):
        uci.get_section(data, "openvpn", "openwrt_first")

    assert path.exists() is False