#
#   Copyright © 2023 Miriam Melina Gamboa Valdez
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

import json

import gevent
from flask import jsonify, request
from isardvdi_common.api_exceptions import Error
from isardvdi_common.tokens import get_jwt_payload

from api import app, socketio

from ..libv2.api_admin import get_user_migration_config, update_user_migration_config
from ..libv2.api_auth import generate_migrate_user_token, import_migrate_user_token
from ..libv2.api_users import ApiUsers
from ..libv2.validators import _validate_item
from .decorators import has_token, is_admin, ownsUserId

users = ApiUsers()


@app.route("/api/v3/admin/config/user_migration", methods=["GET"])
@is_admin
def api_v3_admin_config_migration(payload):
    """

    Endpoint to retrieve the migration configuration

    :param payload: The payload of the request
    :type payload: dict
    :return: The quota check status
    :rtype: Set with Flask response values and data in JSON

    """
    return (
        json.dumps(get_user_migration_config()),
        200,
        {"Content-Type": "application/json"},
    )


@app.route("/api/v3/admin/config/user_migration", methods=["PUT"])
@is_admin
def api_v3_admin_config_migration_update(payload):
    """

    Endpoint to update the migration configuration

    :param payload: The payload of the request
    :type payload: dict
    :return: The quota check status
    :rtype: Set with Flask response values and data in JSON

    """
    if not request.is_json:
        raise Error(
            description="No JSON in body request with user_migration configuration specifications",
        )
    request_json = request.get_json()
    data = _validate_item("user_migration_update", request_json)
    return (
        json.dumps(update_user_migration_config(data)),
        200,
        {"Content-Type": "application/json"},
    )


@app.route("/api/v3/user_migration/export", methods=["POST"])
@has_token
def api_v3_user_migration_export(payload):
    """

    Endpoint to start the user migration process

    :param payload: Data from JWT token
    :type payload: dict
    :return: The user migration process status
    :rtype: Set with Flask response values and data in JSON

    """
    token = generate_migrate_user_token(payload["user_id"])["token"]
    token_data = get_jwt_payload(token)
    users.register_migration(token, token_data["user_id"])
    return (
        json.dumps({"token": token}),
        200,
        {"Content-Type": "application/json"},
    )


@app.route("/api/v3/user_migration/import", methods=["POST"])
@has_token
def api_v3_user_migration_import(payload):
    """

    Endpoint to continue the user migration process to a target user

    :param payload: Data from JWT token
    :type payload: dict

    """
    if not request.is_json:
        raise Error(
            description="No JSON in body request with user_migration configuration specifications",
        )
    request_json = request.get_json()
    data = _validate_item("user_migration_import", request_json)
    users.get_user_migration(data["token"])
    try:
        import_migrate_user_token(data["token"])
    # If the token is expired delete the migration
    except Error as e:
        if e.error.get("description_code") == "token_invalid":
            users.delete_user_migration(data["token"])
        raise e
    users.update_user_migration(
        data["token"], "imported", target_user_id=payload["user_id"], import_time=True
    )
    return (
        json.dumps({}),
        200,
        {"Content-Type": "application/json"},
    )


@app.route("/api/v3/user_migration/items", methods=["GET"])
@has_token
def api_v3_user_migration_list(payload):
    """

    Endpoint to retrieve the items in the user migration process

    :param payload: Data from JWT token
    :type payload: dict
    :return: The list of items in the user migration process
    :rtype: Set with Flask response values and data in JSON

    """
    user_migration = users.get_user_migration_by_target_user(payload["user_id"])
    errors = []
    try:
        import_migrate_user_token(user_migration["token"])
    # If the token is expired delete the migration
    except Error as e:
        if e.error.get("description_code") == "token_invalid":
            users.delete_user_migration(user_migration["token"])
        errors = [
            {
                "description": "The user migration token is not valid.",
                "description_code": "invalid_token",
            }
        ]
    errors += users.check_valid_migration(
        user_migration["origin_user"], payload["user_id"]
    )

    if errors:
        return (
            json.dumps({"errors": errors}),
            428,
            {"Content-Type": "application/json"},
        )

    return (
        json.dumps(users._delete_checks([user_migration["origin_user"]], "user")),
        200,
        {"Content-Type": "application/json"},
    )


@app.route("/api/v3/user_migration/auto", methods=["POST"])
@has_token
def api_v3_user_migration_auto(payload):
    """

    Endpoint to migrate the user items automatically

    :param payload: Data from JWT token
    :type payload: dict
    :return: The user migration process status
    :rtype: Set with Flask response values and data in JSON

    """
    user_migration = users.get_user_migration_by_target_user(payload["user_id"])
    errors = []
    try:
        import_migrate_user_token(user_migration["token"])
    # If the token is expired delete the migration
    except Error as e:
        if e.error.get("description_code") == "token_invalid":
            users.delete_user_migration(user_migration["token"])
        errors = [
            {
                "description": "The user migration token is not valid.",
                "description_code": "invalid_token",
            }
        ]
    errors += users.check_valid_migration(
        user_migration["origin_user"], payload["user_id"]
    )

    if errors:
        return (
            json.dumps({"errors": errors}),
            428,
            {"Content-Type": "application/json"},
        )

    gevent.spawn(
        users.process_automigrate_user,
        user_migration["origin_user"],
        payload["user_id"],
        user_migration["token"],
    )
    return (
        json.dumps({}),
        200,
        {"Content-Type": "application/json"},
    )
