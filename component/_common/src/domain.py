#
#   IsardVDI - Open Source KVM Virtual Desktops based on KVM Linux and dockers
#   Copyright (C) 2023 Simó Albert i Beltran
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from .rethink_custom_base_factory import RethinkCustomBase
from .storage import Storage


class Domain(RethinkCustomBase):
    """
    Manage Domain Objects

    Use constructor with keyword arguments to create new Domain Objects or
    update an existing one using id keyword. Use constructor with id as
    first argument to create an object representing an existing Domain Object.
    """

    _rdb_table = "domains"

    @property
    def storage_ready(self):
        """
        Returns True if storages are ready, otherwise False
        """
        disks = self.create_dict.get("hardware", {}).get("disks", [])
        for disk in disks:
            storage_id = disk.get("storage_id")
            if storage_id and Storage(storage_id).status != "ready":
                return False
        return True
