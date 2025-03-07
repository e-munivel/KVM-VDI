# Copyright 2017 the Isard-vdi project authors:
#      Josep Maria Viñolas Auquer
#      Alberto Larraz Dalmases
# License: AGPLv3

import queue
import random
import time

#!/usr/bin/env python
# coding=utf-8
from decimal import Decimal
from threading import Thread

import pytz
import rethinkdb as r
from flask import current_app

from webapp import app

from .flask_rethink import RethinkDB

db = RethinkDB(app)
db.init_app(app)

from datetime import datetime, timedelta

from apscheduler.jobstores.rethinkdb import RethinkDBJobStore
from apscheduler.schedulers.background import BackgroundScheduler

from ..lib.log import *


class isardScheduler:
    def __init__(self):
        """
        JOB SCHEDULER
        """
        self.rStore = RethinkDBJobStore()

        self.scheduler = BackgroundScheduler(timezone=pytz.timezone("UTC"))
        self.scheduler.add_jobstore(
            "rethinkdb",
            self.rStore,
            database="isard",
            table="scheduler_jobs",
            host=app.config["RETHINKDB_HOST"],
            port=app.config["RETHINKDB_PORT"],
            auth_key="",
        )
        self.scheduler.remove_all_jobs()
        # self.scheduler.add_job(alarm, 'date', run_date=alarm_time, args=[datetime.now()])
        # app.sched.shutdown(wait=False)
        # self.add_scheduler('interval','stop_shutting_down_desktops','0','1')
        self.turnOn()
        self.add_scheduler("interval", "stop_shutting_down_desktops", "0", "1")

    def add_scheduler(self, kind, action, hour, minute):
        id = kind + "_" + action + "_" + str(hour) + str(minute)
        function = getattr(isardScheduler, action)
        if kind == "cron":
            self.scheduler.add_job(
                function,
                kind,
                hour=int(hour),
                minute=int(minute),
                jobstore=self.rStore,
                replace_existing=True,
                id=id,
            )
        if kind == "interval":
            self.scheduler.add_job(
                function,
                kind,
                hours=int(hour),
                minutes=int(minute),
                jobstore=self.rStore,
                replace_existing=True,
                id=id,
            )
        if kind == "date":
            alarm_time = datetime.now() + timedelta(
                hours=int(hour), minutes=int(minute)
            )
            self.scheduler.add_job(
                function,
                kind,
                run_date=alarm_time,
                jobstore=self.rStore,
                replace_existing=True,
                id=id,
            )
        with app.app_context():
            r.table("scheduler_jobs").get(id).update(
                {
                    "kind": kind,
                    "action": action,
                    "name": action.replace("_", " "),
                    "hour": hour,
                    "minute": minute,
                }
            ).run(db.conn)
        return True

    """
    Scheduler actions
    """

    def stop_domains():
        with app.app_context():
            r.table("domains").get_all("Started", index="status").update(
                {"status": "Stopping"}
            ).run(db.conn)

    def stop_domains_without_viewer():
        with app.app_context():
            r.table("domains").get_all("Started", index="status").filter(
                {"viewer": {"client_since": False}}
            ).update({"status": "Stopping"}).run(db.conn)

    def stop_shutting_down_desktops():
        with app.app_context():
            domains = (
                r.table("domains")
                .get_all("Shutting-down", index="status")
                .pluck("id", "accessed")
                .run(db.conn)
            )
            t = time.time()
            for d in domains:
                if d["accessed"] + 1.9 * 60 < t:  # 2 minutes * 60 seconds
                    r.table("domains").get(d["id"]).update(
                        {"status": "Stopping", "accessed": time.time()}
                    ).run(db.conn)

    def check_ephimeral_status():
        with app.app_context():
            domains = (
                r.table("domains")
                .get_all("Started", index="status")
                .has_fields("ephimeral")
                .pluck("id", "ephimeral", "history_domain")
                .run(db.conn)
            )
            t = time.time()
            for d in domains:
                if (
                    d["history_domain"][0]["when"] + int(d["ephimeral"]["minutes"]) * 60
                    < t
                ):
                    r.table("domains").get(d["id"]).update(
                        {"status": d["ephimeral"]["action"]}
                    ).run(db.conn)

    def backup_database():
        app.adminapi.backup_db()

    def turnOff(self):
        self.scheduler.shutdown()

    def turnOn(self):
        self.scheduler.start()

    def removeJobs(self):
        self.scheduler.remove_all_jobs()

    """
    BULK ACTIONS
    """

    def bulk_action(self, table, tbl_filter, tbl_update):
        with app.app_context():
            log.info(
                "BULK ACTION: Table {}, Filter {}, Update {}".format(
                    table, filter, update
                )
            )
            r.table(table).filter(filter).update(update).run(db.conn)
            r.table(table).filter({"status": "Unknown"}).update(
                {"status": "Stopping"}
            ).run(db.conn)
