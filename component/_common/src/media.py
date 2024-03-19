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
from .task import Task


class Media(RethinkCustomBase):
    """
    Manage Media Objects

    Use constructor with keyword arguments to create new Media Objects or
    update an existing one using id keyword. Use constructor with id as
    first argument to create an object representing an existing Media Object.
    """

    _rdb_table = "media"

    def create_task(self, *args, **kwargs):
        """
        Create Task for a Media.
        """
        if "blocking" in kwargs:
            blocking = kwargs.pop("blocking")
        else:
            blocking = True
        if (
            blocking
            and self.task
            and Task.exists(self.task)
            and Task(self.task).pending
        ):
            raise Exception(
                "precondition_required",
                f"Media {self.id} has the pending task {self.task}",
            )
        self.task = Task(*args, **kwargs).id
