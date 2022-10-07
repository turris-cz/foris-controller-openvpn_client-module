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

import pathlib
import textwrap

import pytest
from foris_controller.exceptions import UciRecordNotFound
from foris_controller_testtools.fixtures import (
    FILE_ROOT_PATH,
    UCI_CONFIG_DIR_PATH,
    backend,
    infrastructure,
    init_script_result,
    network_restart_command,
    notify_api,
    only_backends,
    uci_configs_init,
)
from foris_controller_testtools.utils import (
    FileFaker,
    get_uci_module,
    network_restart_was_called,
    sh_was_called,
)

from .conftest import CMDLINE_SCRIPT_ROOT, file_root


@pytest.fixture(scope="function")
def ubus_service_list_cmd(request):

    # ubus call service list '{"name": "openvpn"}'
    content = """\
#!/bin/sh

cat << EOF
{
    "openvpn": {
        "instances": {
            "openwrt_first": {
                "running": false,
                "pid": 2827,
                "command": [
                    "\/usr\/sbin\/openvpn",
                    "--syslog",
                    "openvpn(openwrt_first)",
                    "--status",
                    "\/var\/run\/openvpn.openwrt_first.status",
                    "--cd",
                    "\/var\/etc",
                    "--config",
                    "openvpn-openwrt_first.conf"
                ],
                "term_timeout": 15,
                "respawn": {
                    "threshold": 3600,
                    "timeout": 5,
                    "retry": -1
                }
            },
            "openwrt_second": {
                "running": false,
                "pid": 2830,
                "command": [
                    "\/usr\/sbin\/openvpn",
                    "--syslog",
                    "openvpn(openwrt_second)",
                    "--status",
                    "\/var\/run\/openvpn.openwrt_second.status",
                    "--cd",
                    "\/var\/etc",
                    "--config",
                    "openvpn-openwrt_second.conf"
                ],
                "term_timeout": 15,
                "respawn": {
                    "threshold": 3600,
                    "timeout": 5,
                    "retry": -1
                }
            }
        }
    }
}
EOF
"""  # noqa
    with FileFaker(CMDLINE_SCRIPT_ROOT, "/bin/ubus", True, textwrap.dedent(content)) as f:
        yield f


def add(infrastructure, id, config, username=None, password=None):
    msg_data = {"id": id, "config": config}
    if username is not None and password is not None:
        msg_data["credentials"] = {
            "username": username,
            "password": password
        }

    return infrastructure.process_message(
        {
            "module": "openvpn_client",
            "action": "add",
            "kind": "request",
            "data": msg_data,
        }
    )


def set(infrastructure, id, enabled, username=None, password=None):
    msg_data = {"id": id, "enabled": enabled}
    if username is not None and password is not None:
        msg_data["credentials"] = {
            "username": username,
            "password": password
        }

    return infrastructure.process_message(
        {
            "module": "openvpn_client",
            "action": "set",
            "kind": "request",
            "data": msg_data,
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


def test_list(infrastructure, ubus_service_list_cmd):
    res = infrastructure.process_message(
        {"module": "openvpn_client", "action": "list", "kind": "request"}
    )
    assert "error" not in res
    assert "data" in res
    assert "clients" in res["data"]


def test_complex(
    uci_configs_init,
    init_script_result,
    infrastructure,
    network_restart_command,
    ubus_service_list_cmd,
):
    filters = [("openvpn_client", "add")]
    notifications = infrastructure.get_notifications(filters=filters)

    # add new
    res = add(infrastructure, "first", "1")
    assert "errors" not in res
    assert res["data"]["result"]
    assert {
        "id": "first",
        "enabled": False,
        "running": False,
        "credentials": {"username": "", "password": ""}
    } in list(infrastructure)

    notifications = infrastructure.get_notifications(notifications, filters=filters)
    assert notifications[-1] == {
        "module": "openvpn_client",
        "action": "add",
        "kind": "notification",
        "data": {"id": "first"},
    }

    # NOTE: We do not care about running state of the openvpn instances,
    # therefore it is mocked to always return {"running": false}.

    # add existing
    res = add(infrastructure, "first", "2")
    assert "errors" not in res
    assert not res["data"]["result"]
    assert {
        "id": "first",
        "enabled": False,
        "running": False,
        "credentials": {"username": "", "password": ""}
    } in list(infrastructure)

    # set
    filters = [("openvpn_client", "set")]
    notifications = infrastructure.get_notifications(filters=filters)

    res = set(infrastructure, "first", True)
    assert "errors" not in res
    assert res["data"]["result"]
    assert {
        "id": "first",
        "enabled": True,
        "running": False,
        "credentials": {"username": "", "password": ""}
    } in list(infrastructure)

    notifications = infrastructure.get_notifications(notifications, filters=filters)
    assert notifications[-1] == {
        "module": "openvpn_client",
        "action": "set",
        "kind": "notification",
        "data": {"id": "first", "enabled": True},
    }

    res = set(infrastructure, "first", False)
    assert "errors" not in res
    assert res["data"]["result"]
    assert {
        "id": "first",
        "enabled": False,
        "running": False,
        "credentials": {"username": "", "password": ""}
    } in list(infrastructure)

    notifications = infrastructure.get_notifications(notifications, filters=filters)
    assert notifications[-1] == {
        "module": "openvpn_client",
        "action": "set",
        "kind": "notification",
        "data": {"id": "first", "enabled": False},
    }

    # set missing
    res = set(infrastructure, "second", False)
    assert "errors" not in res
    assert not res["data"]["result"]
    assert {
        "id": "first",
        "enabled": False,
        "running": False,
        "credentials": {"username": "", "password": ""}
    } in list(infrastructure)

    # del
    filters = [("openvpn_client", "del")]
    notifications = infrastructure.get_notifications(filters=filters)

    res = delete(infrastructure, "first")
    assert "errors" not in res
    assert res["data"]["result"]
    assert "first" not in {e["id"] for e in list(infrastructure)}

    notifications = infrastructure.get_notifications(notifications, filters=filters)
    assert notifications[-1] == {
        "module": "openvpn_client",
        "action": "del",
        "kind": "notification",
        "data": {"id": "first"},
    }

    # del missing (deleted)
    res = delete(infrastructure, "first")
    assert "errors" not in res
    assert not res["data"]["result"]
    assert "first" not in {e["id"] for e in list(infrastructure)}


def test_complex_with_credentials(
    uci_configs_init,
    init_script_result,
    infrastructure,
    network_restart_command,
    ubus_service_list_cmd,
):
    filters = [("openvpn_client", "add")]
    notifications = infrastructure.get_notifications(filters=filters)

    # NOTE: We do not care about running state of the openvpn instances,
    # therefore it is mocked to always return {"running": false}.

    # add new
    res = add(infrastructure, "with_creds", "1", "myuser", "p@ssw0rd")
    assert "errors" not in res
    assert res["data"]["result"]
    assert {
        "id": "with_creds",
        "enabled": False,
        "running": False,
        "credentials": {"username": "myuser", "password": "p@ssw0rd"}
    } in list(infrastructure)

    notifications = infrastructure.get_notifications(notifications, filters=filters)
    assert notifications[-1] == {
        "module": "openvpn_client",
        "action": "add",
        "kind": "notification",
        "data": {"id": "with_creds"},
    }

    # update credentials
    res = set(infrastructure, "with_creds", False, "new_user", "123456")
    assert "errors" not in res
    assert res["data"]["result"]
    assert {
        "id": "with_creds",
        "enabled": False,
        "running": False,
        "credentials": {"username": "new_user", "password": "123456"}
    } in list(infrastructure)

    # just toggle enabled status and leave credentials be
    res = set(infrastructure, "with_creds", True)
    assert "errors" not in res
    assert res["data"]["result"]
    assert {
        "id": "with_creds",
        "enabled": True,
        "running": False,
        "credentials": {"username": "new_user", "password": "123456"}
    } in list(infrastructure)

    # reset credentials
    res = set(infrastructure, "with_creds", True, "", "")
    assert "errors" not in res
    assert res["data"]["result"]
    assert {
        "id": "with_creds",
        "enabled": True,
        "running": False,
        "credentials": {"username": "", "password": ""}
    } in list(infrastructure)


@pytest.mark.only_backends(["openwrt"])
def test_complex_openwrt(
    uci_configs_init,
    init_script_result,
    infrastructure,
    network_restart_command,
    ubus_service_list_cmd,
):
    uci = get_uci_module(infrastructure.name)

    assert len(list(infrastructure)) == 0

    # add
    res = add(infrastructure, "openwrt_first", "config content")
    assert res["data"]["result"]

    assert network_restart_was_called([])
    assert sh_was_called(["/etc/init.d/openvpn", "restart"])

    with uci.UciBackend(UCI_CONFIG_DIR_PATH) as backend:
        data = backend.read()
    assert uci.parse_bool(uci.get_option_named(data, "openvpn", "openwrt_first", "enabled")) is False
    assert (
        uci.parse_bool(uci.get_option_named(data, "openvpn", "openwrt_first", "_client_foris"))
        is True
    )
    assert (
        uci.get_option_named(data, "openvpn", "openwrt_first", "config")
        == "/etc/openvpn/foris/openwrt_first.conf"
    )
    # username + password should be unset
    assert uci.get_option_named(data, "openvpn", "openwrt_first", "username", "") == ""
    assert uci.get_option_named(data, "openvpn", "openwrt_first", "password", "") == ""

    path = pathlib.Path(FILE_ROOT_PATH) / "etc/openvpn/foris/openwrt_first.conf"

    assert path.exists()
    assert path.read_text() == "config content"

    # test list
    clients = list(infrastructure)
    assert clients == [
        {
            "id": "openwrt_first",
            "enabled": False,
            "running": False,
            "credentials": {"username": "", "password": ""}
        }
    ]

    # set
    res = set(infrastructure, "openwrt_first", True)
    assert res["data"]["result"]

    with uci.UciBackend(UCI_CONFIG_DIR_PATH) as backend:
        data = backend.read()

    assert network_restart_was_called([])
    assert sh_was_called(["/etc/init.d/openvpn", "restart"])

    assert (
        uci.parse_bool(uci.get_option_named(data, "openvpn", "openwrt_first", "enabled")) is True
    )

    # set it back
    res = set(infrastructure, "openwrt_first", False)
    assert res["data"]["result"]

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


@pytest.mark.only_backends(["openwrt"])
def test_complex_with_credentials_openwrt(
    uci_configs_init,
    init_script_result,
    infrastructure,
    network_restart_command,
    ubus_service_list_cmd,
):
    """Test that openvpn credentials are succesfully stored and read back."""
    uci = get_uci_module(infrastructure.name)

    assert len(list(infrastructure)) == 0

    # add
    res = add(infrastructure, "openwrt_creds", "config content", "myuser", "p@ssw0rd")
    assert res["data"]["result"]

    assert network_restart_was_called([])
    assert sh_was_called(["/etc/init.d/openvpn", "restart"])

    with uci.UciBackend(UCI_CONFIG_DIR_PATH) as backend:
        data = backend.read()
    assert uci.parse_bool(uci.get_option_named(data, "openvpn", "openwrt_creds", "enabled")) is False
    assert (
        uci.parse_bool(uci.get_option_named(data, "openvpn", "openwrt_creds", "_client_foris"))
        is True
    )
    assert (
        uci.get_option_named(data, "openvpn", "openwrt_creds", "config")
        == "/etc/openvpn/foris/openwrt_creds.conf"
    )
    assert uci.get_option_named(data, "openvpn", "openwrt_creds", "username") == "myuser"
    assert uci.get_option_named(data, "openvpn", "openwrt_creds", "password") == "p@ssw0rd"

    path = pathlib.Path(FILE_ROOT_PATH) / "etc/openvpn/foris/openwrt_creds.conf"

    assert path.exists()
    assert path.read_text() == "config content"

    # test list
    clients = list(infrastructure)
    assert clients == [
        {
            "id": "openwrt_creds",
            "enabled": False,
            "running": False,
            "credentials": {"username": "myuser", "password": "p@ssw0rd"}
        }
    ]

    # change credentials
    res = set(infrastructure, "openwrt_creds", False, "new_user", "123456")
    assert res["data"]["result"]

    with uci.UciBackend(UCI_CONFIG_DIR_PATH) as backend:
        data = backend.read()

    assert network_restart_was_called([])
    assert sh_was_called(["/etc/init.d/openvpn", "restart"])

    assert (
        uci.parse_bool(uci.get_option_named(data, "openvpn", "openwrt_creds", "enabled")) is False
    )
    assert uci.get_option_named(data, "openvpn", "openwrt_creds", "username") == "new_user"
    assert uci.get_option_named(data, "openvpn", "openwrt_creds", "password") == "123456"

    # try to update just one of a pair username + password - it should not change the previous credentials
    res = set(infrastructure, "openwrt_creds", False, username="another_new_user")
    assert res["data"]["result"]

    with uci.UciBackend(UCI_CONFIG_DIR_PATH) as backend:
        data = backend.read()

    assert (
        uci.parse_bool(uci.get_option_named(data, "openvpn", "openwrt_creds", "enabled")) is False
    )
    assert uci.get_option_named(data, "openvpn", "openwrt_creds", "username") == "new_user"
    assert uci.get_option_named(data, "openvpn", "openwrt_creds", "password") == "123456"

    res = set(infrastructure, "openwrt_creds", False, password="newPassword")
    assert res["data"]["result"]

    with uci.UciBackend(UCI_CONFIG_DIR_PATH) as backend:
        data = backend.read()

    assert (
        uci.parse_bool(uci.get_option_named(data, "openvpn", "openwrt_creds", "enabled")) is False
    )
    assert uci.get_option_named(data, "openvpn", "openwrt_creds", "username") == "new_user"
    assert uci.get_option_named(data, "openvpn", "openwrt_creds", "password") == "123456"

    # just toggle enabled
    res = set(infrastructure, "openwrt_creds", True)
    assert res["data"]["result"]

    with uci.UciBackend(UCI_CONFIG_DIR_PATH) as backend:
        data = backend.read()

    assert network_restart_was_called([])
    assert sh_was_called(["/etc/init.d/openvpn", "restart"])

    assert (
        uci.parse_bool(uci.get_option_named(data, "openvpn", "openwrt_creds", "enabled")) is True
    )
    assert uci.get_option_named(data, "openvpn", "openwrt_creds", "username") == "new_user"
    assert uci.get_option_named(data, "openvpn", "openwrt_creds", "password") == "123456"

    # clear credentials
    res = set(infrastructure, "openwrt_creds", True, "", "")
    assert res["data"]["result"]

    with uci.UciBackend(UCI_CONFIG_DIR_PATH) as backend:
        data = backend.read()

    assert network_restart_was_called([])
    assert sh_was_called(["/etc/init.d/openvpn", "restart"])

    assert (
        uci.parse_bool(uci.get_option_named(data, "openvpn", "openwrt_creds", "enabled")) is True
    )
    assert uci.get_option_named(data, "openvpn", "openwrt_creds", "username", "") == ""
    assert uci.get_option_named(data, "openvpn", "openwrt_creds", "password", "") == ""


@pytest.mark.parametrize(
    "plain, sanitized",
    [
        ("my-sample-id", "my_sample_id"),
        ("-" * 50, "_" * 50),
        ("-", "_"),
        ("my.sample.id", "my_sample_id"),
        ("." * 50, "_" * 50),
        (".", "_"),
    ],
    ids=["dash", "max-dashes", "min-dashes", "dot", "max-dots", "min-dots"],
)
def test_add(
    uci_configs_init,
    init_script_result,
    infrastructure,
    network_restart_command,
    ubus_service_list_cmd,
    plain,
    sanitized,
):
    res = add(infrastructure, plain, config="config data...")
    assert "errors" not in res
    assert {
        "id": sanitized,
        "enabled": False,
        "running": False,
        "credentials": {"username": "", "password": ""}
    } in list(infrastructure)
