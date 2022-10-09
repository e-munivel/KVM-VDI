from rethinkdb import RethinkDB

from api import app

from .api_exceptions import Error

r = RethinkDB()
import time
import traceback

from .flask_rethink import RDB

db = RDB(app)
db.init_app(app)


def wait_status(
    desktop_id, current_status, wait_seconds=0, interval_seconds=2, raise_exc=True
):
    if wait_seconds == 0:
        return current_status
    seconds = 0
    status = current_status
    while status == current_status and seconds <= wait_seconds:
        time.sleep(interval_seconds)
        seconds += interval_seconds
        with app.app_context():
            try:
                status = (
                    r.table("domains")
                    .get(desktop_id)
                    .pluck("status")["status"]
                    .run(db.conn)
                )
            except:
                raise Error(
                    "not_found",
                    "Desktop not found",
                    traceback.format_exc(),
                    description_code="not_found",
                )
    if status == current_status:
        if raise_exc:
            raise Error(
                "internal_server",
                "Engine could not change "
                + desktop_id
                + " status from "
                + current_status
                + " in "
                + str(wait_seconds),
                traceback.format_exc(),
                description_code="generic_error",
            )
        else:
            return False
    return status


def get_desktop_status(desktop_id):
    with app.app_context():
        try:
            status = (
                r.table("domains")
                .get(desktop_id)
                .pluck("status")["status"]
                .run(db.conn)
            )
        except:
            raise Error(
                "not_found",
                "Desktop not found",
                traceback.format_exc(),
                description_code="not_found",
            )
    return status


def desktop_start(desktop_id, wait_seconds=0, paused=False):
    status = get_desktop_status(desktop_id)
    if status in ["Started", "Starting", "StartingPaused", "CreatingAndStarting"]:
        return True
    if status not in ["Stopped", "Failed"]:
        raise Error(
            "precondition_required",
            "Desktop can't be started from " + status,
            traceback.format_exc(),
            description_code="unable_to_start_desktop_from" + status,
        )
    with app.app_context():
        new_status = "Starting" if not paused else "StartingPaused"
        r.table("domains").get(desktop_id).update(
            {"status": new_status, "accessed": int(time.time())}
        ).run(db.conn)

    return wait_status(desktop_id, new_status, wait_seconds=wait_seconds)


def desktops_start(desktops_ids, wait_seconds=0):
    with app.app_context():
        desktops = list(
            r.table("domains")
            .get_all(r.args(desktops_ids), index="id")
            .pluck("id", "status")
            .run(db.conn)
        )
        desktops_ok = [
            desktop
            for desktop in desktops
            if desktop["status"] in ["Stopped", "Failed"]
        ]
        r.table("domains").get_all(r.args(desktops_ok), index="id").update(
            {"status": "Starting", "accessed": int(time.time())}
        ).run(db.conn)


def desktop_stop(desktop_id, force=False, wait_seconds=0):
    status = get_desktop_status(desktop_id)
    if status in ["Stopped", "Stopping", "Failed"]:
        return status
    if status == "Started":
        if not force:
            with app.app_context():
                r.table("domains").get(desktop_id).update(
                    {"status": "Shutting-down", "accessed": int(time.time())}
                ).run(db.conn)
            return wait_status(desktop_id, "Shutting-down", wait_seconds=wait_seconds)
        else:
            with app.app_context():
                r.table("domains").get(desktop_id).update(
                    {"status": "Shutting-down", "accessed": int(time.time())}
                ).run(db.conn)
            status_changed = wait_status(
                desktop_id,
                "Shutting-down",
                wait_seconds=120,
                raise_exc=False,
                interval_seconds=30,
            )
            if status_changed:
                return status_changed
            else:
                status = "Shutting-down"
    if status == "Shutting-down":
        with app.app_context():
            r.table("domains").get(desktop_id).update(
                {"status": "Stopping", "accessed": int(time.time())}
            ).run(db.conn)
        return wait_status(desktop_id, "Stopping", wait_seconds=wait_seconds)

    raise Error(
        "precondition_required",
        "Desktop can't be stopped from " + status,
        traceback.format_exc(),
        description_code="unable_to_stop_desktop_from" + status,
    )


def desktops_stop(desktops_ids, force=False, wait_seconds=30):
    if force:
        with app.app_context():
            r.table("domains").get_all(r.args(desktops_ids), index="id").filter(
                {"status": "Shutting-down"}
            ).update({"status": "Stopping", "accessed": int(time.time())}).run(db.conn)
            r.table("domains").get_all(r.args(desktops_ids), index="id").filter(
                {"status": "Started"}
            ).update({"status": "Shutting-down", "accessed": int(time.time())}).run(
                db.conn
            )
            time.sleep(wait_seconds)
            r.table("domains").get_all(r.args(desktops_ids), index="id").filter(
                {"status": "Shutting-down"}
            ).update({"status": "Stopping", "accessed": int(time.time())}).run(db.conn)
    else:
        with app.app_context():
            r.table("domains").get_all(r.args(desktops_ids), index="id").filter(
                {"status": "Shutting-down"}
            ).update({"status": "Stopping", "accessed": int(time.time())}).run(db.conn)
            r.table("domains").get_all(r.args(desktops_ids), index="id").filter(
                {"status": "Started"}
            ).update({"status": "Shutting-down", "accessed": int(time.time())}).run(
                db.conn
            )
