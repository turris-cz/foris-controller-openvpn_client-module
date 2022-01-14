# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2022, CZ.NIC z.s.p.o. (https://www.nic.cz/)

import typing


class OpenVPNClientCredentials(typing.TypedDict):
    username: str
    password: str
