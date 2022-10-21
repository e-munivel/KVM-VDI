#
#   Copyright © 2022 Josep Maria Viñolas Auquer
#
#   This file is part of IsardVDI.
#
#   IsardVDI is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or (at your
#   option) any later version.
#
#   IsardVDI is distributed in the hope that it will be useful, but WITHOUT ANY
#   WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
#   FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
#   details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with IsardVDI. If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import os

# from api.libv2 import api_disks_watchdog
from flask import Flask

from api import app

if __name__ == "__main__":
    app.logger.info("Starting application")
    # api_disks_watchdog.start_disks_watchdog()
    debug = True if os.environ["LOG_LEVEL"] == "DEBUG" else False
    app.run(host="0.0.0.0", debug=debug, port=5000)
