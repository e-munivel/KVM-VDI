#!/usr/bin/env python
# coding=utf-8
# Copyright 2017 the Isard-vdi project authors:
#      Josep Maria Viñolas Auquer
#      Alberto Larraz Dalmases
# License: AGPLv3

from rethinkdb import RethinkDB

from api import app

r = RethinkDB()
import logging as log

from rethinkdb.errors import ReqlNonExistenceError, ReqlTimeoutError

from .flask_rethink import RDB

db = RDB(app)
db.init_app(app)


class ApiVpn:
    def active_client(
        self,
        kind,
        client_ip,
        remote_ip=None,
        remote_port=None,
        status=False,
    ):
        # NOTE: Kind will be users/hypers as this are the only two wireguard
        #       interfaces. Remotevpn are handled in users wg interface.
        if kind not in ["users", "hypers"]:
            return False

        connection_data = {
            "connected": status,
            "remote_ip": remote_ip,
            "remote_port": remote_port,
        }

        # Find ip
        if kind == "users":
            with app.app_context():
                if update_insert(
                    r.table("users")
                    .get_all(client_ip, index="wg_client_ip")
                    .update({"vpn": {"wireguard": connection_data}})
                    .run(db.conn)
                ):
                    return True
                if update_insert(
                    r.table("remotevpn")
                    .get_all(client_ip, index="wg_client_ip")
                    .update({"vpn": {"wireguard": connection_data}})
                    .run(db.conn)
                ):
                    return True
        else:  # kind = hypers
            with app.app_context():
                if update_insert(
                    r.table("hypervisors")
                    .get_all(client_ip, index="wg_client_ip")
                    .update({"vpn": {"wireguard": connection_data}})
                    .run(db.conn)
                ):
                    return True


def reset_connection_status(
    kind,
):
    if kind not in ["users", "hypers", "all"]:
        return False
    connection_data = {"connected": False, "remote_ip": None, "remote_port": None}

    # Find ip
    if kind in ["users", "all"]:
        with app.app_context():
            r.table("users").has_fields({"vpn": {"wireguard": "Address"}}).update(
                {"vpn": {"wireguard": connection_data}}
            ).run(db.conn)
    if kind in ["remotevpn", "all"]:
        with app.app_context():
            r.table("remotevpn").has_fields({"vpn": {"wireguard": "Address"}}).update(
                {"vpn": {"wireguard": connection_data}}
            ).run(db.conn)
    if kind in ["hypers", "all"]:
        with app.app_context():
            r.table("hypervisors").has_fields({"vpn": {"wireguard": "Address"}}).update(
                {"vpn": {"wireguard": connection_data}}
            ).run(db.conn)
    return True


def update_insert(dict):
    """
    These are the actions:
    {u'skipped': 0, u'deleted': 1, u'unchanged': 0, u'errors': 0, u'replaced': 0, u'inserted': 0}
    """
    if dict["errors"]:
        return False
    if dict["inserted"] or dict["replaced"]:
        return True
    return False
