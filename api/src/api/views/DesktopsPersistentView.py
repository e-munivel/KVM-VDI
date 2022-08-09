# Copyright 2017 the Isard-vdi project authors:
#      Josep Maria Viñolas Auquer
#      Alberto Larraz Dalmases
# License: AGPLv3

import json
import traceback

from flask import request
from rethinkdb import RethinkDB

r = RethinkDB()

from api import app

from ..libv2.api_exceptions import Error
from ..libv2.quotas import Quotas

quotas = Quotas()

from ..libv2.api_desktops_persistent import ApiDesktopsPersistent

desktops = ApiDesktopsPersistent()

from ..libv2.validators import _validate_item, check_user_duplicated_domain_name
from .decorators import allowedTemplateId, has_token, is_admin_or_manager, ownsDomainId


@app.route("/api/v3/desktop/start/<desktop_id>", methods=["GET"])
@has_token
def api_v3_desktop_start(payload, desktop_id):
    ownsDomainId(payload, desktop_id)
    user_id = desktops.UserDesktop(desktop_id)
    quotas.DesktopStart(user_id)

    # So now we have checked if desktop exists and if we can create and/or start it
    return (
        json.dumps({"id": desktops.Start(desktop_id)}),
        200,
        {"Content-Type": "application/json"},
    )


@app.route("/api/v3/desktops/start", methods=["PUT"])
@has_token
def api_v3_desktops_start(payload):
    try:
        data = request.get_json(force=True)
        desktops_ids = data["desktops_ids"]
    except:
        Error(
            "bad_request",
            "DesktopS start incorrect body data",
            traceback.format_exc(),
        )

    for desktop_id in desktops_ids:
        ownsDomainId(payload, desktop_id)
        user_id = desktops.UserDesktop(desktop_id)
        quotas.DesktopStart(user_id)

    # So now we have checked if desktop exists and if we can create and/or start it
    return (
        json.dumps({}),
        200,
        {"Content-Type": "application/json"},
    )


@app.route("/api/v3/desktop/stop/<desktop_id>", methods=["GET"])
@has_token
def api_v3_desktop_stop(payload, desktop_id):
    ownsDomainId(payload, desktop_id)
    user_id = desktops.UserDesktop(desktop_id)

    return (
        json.dumps({"id": desktops.Stop(desktop_id)}),
        200,
        {"Content-Type": "application/json"},
    )


@app.route("/api/v3/desktops/stop", methods=["PUT"])
@has_token
def api_v3_desktops_stop(payload, desktop_id):
    try:
        data = request.get_json(force=True)
        desktops_ids = data["desktops_ids"]
    except:
        Error(
            "bad_request",
            "DesktopS start incorrect body data",
            traceback.format_exc(),
        )
    for desktop_id in desktops_ids:
        ownsDomainId(payload, desktop_id)
        user_id = desktops.UserDesktop(desktop_id)

    return (
        json.dumps({}),
        200,
        {"Content-Type": "application/json"},
    )


@app.route("/api/v3/persistent_desktop", methods=["POST"])
@has_token
def api_v3_persistent_desktop_new(payload):
    try:
        data = request.get_json(force=True)
    except:
        Error(
            "bad_request",
            "Desktop persistent add incorrect body data",
            traceback.format_exc(),
        )

    data = _validate_item("desktop_from_template", data)
    allowedTemplateId(payload, data["template_id"])
    quotas.DesktopCreate(payload["user_id"])

    desktop_id = desktops.NewFromTemplate(
        desktop_name=data["name"],
        desktop_description=data["description"],
        template_id=data["template_id"],
        user_id=payload["user_id"],
        new_data=data,
        image=data.get("image"),
    )
    return json.dumps({"id": desktop_id}), 200, {"Content-Type": "application/json"}


# Bulk desktops action
@app.route("/api/v3/persistent_desktop/bulk", methods=["POST"])
@is_admin_or_manager
def api_v3_persistent_desktop_bulk_new(payload):
    try:
        data = request.get_json(force=True)
    except:
        Error(
            "bad_request",
            "Desktop persistent add incorrect body data",
            traceback.format_exc(),
        )
    data = _validate_item("desktops_from_template", data)
    allowedTemplateId(payload, data["template_id"])
    desktops.BulkDesktops(payload, data)

    return json.dumps({}), 200, {"Content-Type": "application/json"}


@app.route("/api/v3/desktop/from/media", methods=["POST"])
@has_token
def api_v3_desktop_from_media(payload):
    try:
        data = request.get_json(force=True)
    except:
        Error(
            "bad_request",
            "Desktop persistent add incorrect body data",
            traceback.format_exc(),
        )
    data["user_id"] = payload["user_id"]
    data = _validate_item("desktop_from_media", data)
    quotas.DesktopCreate(payload["user_id"])
    desktop_id = desktops.NewFromMedia(payload, data)
    return json.dumps({"id": desktop_id}), 200, {"Content-Type": "application/json"}


@app.route("/api/v3/domain/<domain_id>", methods=["PUT"])
@has_token
def api_v3_domain_edit(payload, domain_id):
    try:
        data = request.get_json(force=True)
    except:
        raise Error(
            "bad_request",
            "Desktop edit incorrect body data",
            traceback.format_exc(),
        )
    data["id"] = domain_id
    data = _validate_item("desktop_update", data)
    ownsDomainId(payload, domain_id)
    desktop = desktops.Get(desktop_id=domain_id)
    if data.get("name"):
        check_user_duplicated_domain_name(data["id"], data["name"], desktop["user"])

    admin_or_manager = True if payload["role_id"] in ["manager", "admin"] else False
    desktops.Update(domain_id, data, admin_or_manager)
    return (
        json.dumps(data),
        200,
        {"Content-Type": "application/json"},
    )


@app.route("/api/v3/desktop/jumperurl/<desktop_id>", methods=["GET"])
@has_token
def api_v3_admin_viewer(payload, desktop_id):
    ownsDomainId(payload, desktop_id)
    data = desktops.JumperUrl(desktop_id)
    return (
        json.dumps(data),
        200,
        {"Content-Type": "application/json"},
    )


@app.route("/api/v3/desktop/jumperurl_reset/<desktop_id>", methods=["PUT"])
@has_token
def admin_jumperurl_reset(payload, desktop_id):
    ownsDomainId(payload, desktop_id)
    try:
        data = request.get_json()
    except:
        raise Error("bad_request", "Bad body data", traceback.format_exc())
    response = desktops.JumperUrlReset(desktop_id, disabled=data.get("disabled"))
    return (
        json.dumps(response),
        200,
        {"Content-Type": "application/json"},
    )


@app.route("/api/v3/desktop/<desktop_id>", methods=["DELETE"])
@has_token
def api_v3_desktop_delete(payload, desktop_id):
    ownsDomainId(payload, desktop_id)
    desktops.Delete(desktop_id)
    return json.dumps({}), 200, {"Content-Type": "application/json"}
