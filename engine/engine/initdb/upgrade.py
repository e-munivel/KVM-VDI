# Copyright 2017 the Isard-vdi project authors:
#      Josep Maria Viñolas Auquer
#      Alberto Larraz Dalmases
# License: AGPLv3

# !/usr/bin/env python
# coding=utf-8

import sys
import time

import requests
import rethinkdb as r

from .lib import *
from .log import *

""" 
Update to new database release version when new code version release
"""
release_version = 24
# release 24: Add missing domains created from qcow2 media disk image field
# release 23: Added enabled to templates
# release 22: Upgrade domains image field
# release 21: Added secondary wg_client_ip index to users.
#             Added secondary wg_client_ip index to remotevpn
# release 20: forced_hyp should be a list if not False
# release 19: Update hypervisors_pools based on actual hypervisors in db
# release 18: Replace deployment id # to = (and also to domains)
# release 16: Added secondary wg_mac index to domains

tables = [
    "config",
    "hypervisors",
    "hypervisors_pools",
    "domains",
    "media",
    "videos",
    "graphics",
    "users",
    "roles",
    "groups",
    "interfaces",
    "deployments",
    "remotevpn",
]


class Upgrade(object):
    def __init__(self):
        cfg = loadConfig()
        self.conf = cfg.cfg()

        self.conn = False
        self.cfg = False
        try:
            self.conn = r.connect(
                self.conf["RETHINKDB_HOST"],
                self.conf["RETHINKDB_PORT"],
                self.conf["RETHINKDB_DB"],
            ).repl()
        except Exception as e:
            log.error(
                "Database not reacheable at "
                + self.conf["RETHINKDB_HOST"]
                + ":"
                + self.conf["RETHINKDB_PORT"]
            )
            sys.exit()

        if self.conn is not False and r.db_list().contains(
            self.conf["RETHINKDB_DB"]
        ).run(self.conn):
            if r.table_list().contains("config").run(self.conn):
                ready = False
                while not ready:
                    try:
                        self.cfg = r.table("config").get(1).run(self.conn)
                        ready = True
                    except Exception as e:
                        log.info("Waiting for database to be ready...")
                        time.sleep(1)
                log.info("Your actual database version is: " + str(self.cfg["version"]))
                if release_version > self.cfg["version"]:
                    log.warning(
                        "Database upgrade needed! You have version "
                        + str(self.cfg["version"])
                        + " and source code is for version "
                        + str(release_version)
                        + "!!"
                    )
                else:
                    log.info("No database upgrade needed.")
        self.upgrade_if_needed()

    def do_backup(self):
        None

    def upgrade_if_needed(self):
        print(release_version)
        print(self.cfg["version"])
        if not release_version > self.cfg["version"]:
            return False
        apply_upgrades = [
            i for i in range(self.cfg["version"] + 1, release_version + 1)
        ]
        log.info("Now will upgrade database versions: " + str(apply_upgrades))
        for version in apply_upgrades:
            for table in tables:
                eval("self." + table + "(" + str(version) + ")")

        r.table("config").get(1).update({"version": release_version}).run(self.conn)

    """
    CONFIG TABLE UPGRADES
    """

    def config(self, version):
        table = "config"
        d = r.table(table).get(1).run(self.conn)
        log.info("UPGRADING " + table + " TABLE TO VERSION " + str(version))
        if version == 1:

            """CONVERSION FIELDS PRE CHECKS"""
            try:
                if not self.check_done(d, ["grafana"], [["engine", "carbon"]]):
                    ##### CONVERSION FIELDS
                    cfg["grafana"] = {
                        "active": d["engine"]["carbon"]["active"],
                        "url": d["engine"]["carbon"]["server"],
                        "web_port": 80,
                        "carbon_port": d["engine"]["carbon"]["port"],
                        "graphite_port": 3000,
                    }
                    r.table(table).update(cfg).run(self.conn)
            except Exception as e:
                log.error(
                    "Could not update table "
                    + table
                    + " conversion fields for db version "
                    + str(version)
                    + "!"
                )
                log.error("Error detail: " + str(e))

            """ NEW FIELDS PRE CHECKS """
            try:
                if not self.check_done(
                    d, ["resources", "voucher_access", ["engine", "api", "token"]], []
                ):
                    ##### NEW FIELDS
                    self.add_keys(
                        table,
                        [
                            {
                                "resources": {
                                    "code": False,
                                    "url": "http://www.isardvdi.com:5050",
                                }
                            },
                            {"voucher_access": {"active": False}},
                            {
                                "engine": {
                                    "api": {
                                        "token": "fosdem",
                                        "url": "http://isard-engine",
                                        "web_port": 5555,
                                    }
                                }
                            },
                        ],
                    )
            except Exception as e:
                log.error(
                    "Could not update table "
                    + table
                    + " new fields for db version "
                    + str(version)
                    + "!"
                )
                log.error("Error detail: " + str(e))

            """ REMOVE FIELDS PRE CHECKS """
            try:
                if not self.check_done(d, [], [["engine", "carbon"]]):
                    #### REMOVE FIELDS
                    self.del_keys(table, [{"engine": {"carbon"}}])
            except Exception as e:
                log.error(
                    "Could not update table "
                    + table
                    + " remove fields for db version "
                    + str(version)
                    + "!"
                )
                log.error("Error detail: " + str(e))

        if version == 5:
            d["engine"]["log"]["log_level"] = "WARNING"
            r.table(table).update(d).run(self.conn)

        if version == 6:

            """CONVERSION FIELDS PRE CHECKS"""
            try:
                url = d["engine"]["grafana"]["url"]
            except:
                url = ""
            try:
                if not self.check_done(d, [], ["engine"]):
                    ##### CONVERSION FIELDS
                    d["engine"]["grafana"] = {
                        "active": False,
                        "carbon_port": 2004,
                        "interval": 5,
                        "hostname": "isard-grafana",
                        "url": url,
                    }
                    r.table(table).update(d).run(self.conn)
            except Exception as e:
                log.error(
                    "Could not update table "
                    + table
                    + " conversion fields for db version "
                    + str(version)
                    + "!"
                )
                log.error("Error detail: " + str(e))

            # ~ ''' NEW FIELDS PRE CHECKS '''
            # ~ try:
            # ~ if not self.check_done( d,
            # ~ ['resources','voucher_access',['engine','api','token']],
            # ~ []):
            # ~ ##### NEW FIELDS
            # ~ self.add_keys(table, [
            # ~ {'resources':  {    'code':False,
            # ~ 'url':'http://www.isardvdi.com:5050'}},
            # ~ {'voucher_access':{'active':False}},
            # ~ {'engine':{'api':{  "token": "fosdem",
            # ~ "url": 'http://isard-engine',
            # ~ "web_port": 5555}}}])
            # ~ except Exception as e:
            # ~ log.error('Could not update table '+table+' new fields for db version '+str(version)+'!')
            # ~ log.error('Error detail: '+str(e))

            """ REMOVE FIELDS PRE CHECKS """
            try:
                if not self.check_done(d, [], ["grafana"]):
                    #### REMOVE FIELDS
                    self.del_keys(table, ["grafana"])
            except Exception as e:
                log.error(
                    "Could not update table "
                    + table
                    + " remove fields for db version "
                    + str(version)
                    + "!"
                )
                log.error("Error detail: " + str(e))

        if version == 10:
            try:
                d["resources"]["url"] = "https://repository.isardvdi.com"
                r.table(table).update(d).run(self.conn)
            except Exception as e:
                log.error(
                    "Could not update table "
                    + table
                    + " conversion fields for db version "
                    + str(version)
                    + "!"
                )
                log.error("Error detail: " + str(e))

        return True

    """
    HYPERVISORS TABLE UPGRADES
    """

    def hypervisors(self, version):
        table = "hypervisors"
        data = list(r.table(table).run(self.conn))
        log.info("UPGRADING " + table + " VERSION " + str(version))
        if version == 1:
            for d in data:
                id = d["id"]
                d.pop("id", None)

                """ CONVERSION FIELDS PRE CHECKS """
                # ~ try:
                # ~ if not self.check_done( d,
                # ~ [],
                # ~ []):
                ##### CONVERSION FIELDS
                # ~ cfg['field']={}
                # ~ r.table(table).update(cfg).run(self.conn)
                # ~ except Exception as e:
                # ~ log.error('Could not update table '+table+' remove fields for db version '+str(version)+'!')
                # ~ log.error('Error detail: '+str(e))

                """ NEW FIELDS PRE CHECKS """
                try:
                    if not self.check_done(
                        d, ["viewer_hostname", "viewer_nat_hostname"], []
                    ):
                        ##### NEW FIELDS
                        self.add_keys(
                            table,
                            [
                                {"viewer_hostname": d["hostname"]},
                                {"viewer_nat_hostname": d["hostname"]},
                            ],
                            id=id,
                        )
                except Exception as e:
                    log.error(
                        "Could not update table "
                        + table
                        + " remove fields for db version "
                        + str(version)
                        + "!"
                    )
                    log.error("Error detail: " + str(e))

                """ REMOVE FIELDS PRE CHECKS """
                # ~ try:
                # ~ if not self.check_done( d,
                # ~ [],
                # ~ []):
                #### REMOVE FIELDS
                # ~ self.del_keys(TABLE,[])
                # ~ except Exception as e:
                # ~ log.error('Could not update table '+table+' remove fields for db version '+str(version)+'!')
                # ~ log.error('Error detail: '+str(e))

        if version == 2:
            for d in data:
                id = d["id"]
                d.pop("id", None)

                """ CONVERSION FIELDS PRE CHECKS """
                # ~ try:
                # ~ if not self.check_done( d,
                # ~ [],
                # ~ []):
                ##### CONVERSION FIELDS
                # ~ cfg['field']={}
                # ~ r.table(table).update(cfg).run(self.conn)
                # ~ except Exception as e:
                # ~ log.error('Could not update table '+table+' remove fields for db version '+str(version)+'!')
                # ~ log.error('Error detail: '+str(e))

                """ NEW FIELDS PRE CHECKS """
                try:
                    if not self.check_done(d, ["viewer_nat_offset"], []):
                        ##### NEW FIELDS
                        self.add_keys(table, [{"viewer_nat_offset": 0}], id=id)
                except Exception as e:
                    log.error(
                        "Could not update table "
                        + table
                        + " add fields for db version "
                        + str(version)
                        + "!"
                    )
                    log.error("Error detail: " + str(e))

                """ REMOVE FIELDS PRE CHECKS """
                # ~ try:
                # ~ if not self.check_done( d,
                # ~ [],
                # ~ []):
                #### REMOVE FIELDS
                # ~ self.del_keys(TABLE,[])
                # ~ except Exception as e:
                # ~ log.error('Could not update table '+table+' remove fields for db version '+str(version)+'!')
                # ~ log.error('Error detail: '+str(e))

        if version == 8:
            for d in data:
                id = d["id"]
                d.pop("id", None)

                """ CONVERSION FIELDS PRE CHECKS """
                # ~ try:
                # ~ if not self.check_done( d,
                # ~ [],
                # ~ []):
                ##### CONVERSION FIELDS
                # ~ cfg['field']={}
                # ~ r.table(table).update(cfg).run(self.conn)
                # ~ except Exception as e:
                # ~ log.error('Could not update table '+table+' remove fields for db version '+str(version)+'!')
                # ~ log.error('Error detail: '+str(e))

                """ NEW FIELDS PRE CHECKS """
                try:
                    if not self.check_done(d, ["viewer"], []):
                        ##### NEW FIELDS
                        self.add_keys(
                            table,
                            [
                                {
                                    "viewer": {
                                        "static": d["viewer_hostname"],
                                        "proxy_video": d["viewer_hostname"],
                                        "proxy_hyper_host": d["hostname"],
                                    }
                                }
                            ],
                            id=id,
                        )
                except Exception as e:
                    log.error(
                        "Could not update table "
                        + table
                        + " add fields for db version "
                        + str(version)
                        + "!"
                    )
                    log.error("Error detail: " + str(e))

                """ REMOVE FIELDS PRE CHECKS """
                try:
                    if not self.check_done(
                        d,
                        [],
                        ["viewer_hostname", "viewer_nat_hostname", "viewer_nat_offset"],
                    ):
                        # ~ #### REMOVE FIELDS
                        self.del_keys(
                            table,
                            [
                                "viewer_hostname",
                                "viewer_nat_hostname",
                                "viewer_nat_offset",
                            ],
                        )
                        # ~ self.del_keys(TABLE,['viewer_hostname'])
                        # ~ self.del_keys(TABLE,['viewer_nat_hostname'])
                        # ~ self.del_keys(TABLE,['viewer_nat_offset'])
                except Exception as e:
                    log.error(
                        "Could not update table "
                        + table
                        + " remove fields for db version "
                        + str(version)
                        + "!"
                    )
                    log.error("Error detail: " + str(e))

        if version == 11:
            for d in data:
                id = d["id"]
                d.pop("id", None)

                """ CONVERSION FIELDS PRE CHECKS """
                # ~ try:
                # ~ if not self.check_done( d,
                # ~ [],
                # ~ []):
                ##### CONVERSION FIELDS
                # ~ cfg['field']={}
                # ~ r.table(table).update(cfg).run(self.conn)
                # ~ except Exception as e:
                # ~ log.error('Could not update table '+table+' remove fields for db version '+str(version)+'!')
                # ~ log.error('Error detail: '+str(e))

                """ NEW FIELDS PRE CHECKS """
                try:
                    if id == "isard-hypervisor":
                        if not self.check_done(d, ["hypervisor_number"], []):
                            ##### NEW FIELDS
                            self.add_keys(table, [{"hypervisor_number": 0}], id=id)
                except Exception as e:
                    log.error(
                        "Could not update table "
                        + table
                        + " add fields for db version "
                        + str(version)
                        + "!"
                    )
                    log.error("Error detail: " + str(e))

                """ REMOVE FIELDS PRE CHECKS """

        if version == 13:
            for d in data:
                id = d["id"]
                d.pop("id", None)

                """ CONVERSION FIELDS PRE CHECKS """
                # ~ try:
                # ~ if not self.check_done( d,
                # ~ [],
                # ~ []):
                ##### CONVERSION FIELDS
                # ~ cfg['field']={}
                # ~ r.table(table).update(cfg).run(self.conn)
                # ~ except Exception as e:
                # ~ log.error('Could not update table '+table+' remove fields for db version '+str(version)+'!')
                # ~ log.error('Error detail: '+str(e))

                """ NEW FIELDS PRE CHECKS """
                try:
                    if not self.check_done(d, [], [{"viewer": {"html5_ext_port"}}]):
                        ##### NEW FIELDS
                        self.add_keys(
                            table,
                            [
                                {
                                    "viewer": {
                                        "html5_ext_port": "443",
                                        "spice_ext_port": "80",
                                    }
                                }
                            ],
                            id=id,
                        )
                except Exception as e:
                    log.error(
                        "Could not update table "
                        + table
                        + " add fields for db version "
                        + str(version)
                        + "!"
                    )
                    log.error("Error detail: " + str(e))

                """ REMOVE FIELDS PRE CHECKS """

        if version == 21:
            try:
                r.table(table).index_create(
                    "wg_client_ip", r.row["vpn"]["wireguard"]["Address"]
                ).run(self.conn)
            except:
                log.error(
                    "Could not update table "
                    + table
                    + " index creation for db version "
                    + str(version)
                    + "!"
                )
                log.error("Error detail: " + str(e))

        return True

    """
    HYPERVISORS_POOLS TABLE UPGRADES
    """

    def hypervisors_pools(self, version):
        table = "hypervisors_pools"
        data = list(r.table(table).run(self.conn))
        log.info("UPGRADING " + table + " VERSION " + str(version))
        if version == 1 or version == 3:
            for d in data:
                id = d["id"]
                d.pop("id", None)
                try:
                    """CONVERSION FIELDS PRE CHECKS"""
                    # ~ if not self.check_done( d,

                    # ~ [],
                    # ~ []):
                    ##### CONVERSION FIELDS
                    # ~ cfg['field']={}
                    # ~ r.table(table).update(cfg).run(self.conn)

                    """ NEW FIELDS PRE CHECKS """
                    if not self.check_done(d, [["paths", "media"]], []):
                        ##### NEW FIELDS
                        media = d["paths"]["groups"]  # .copy()
                        # ~ print(media)
                        medialist = []
                        for m in media:
                            m["path"] = m["path"].split("groups")[0] + "media"
                            medialist.append(m)
                        d["paths"]["media"] = medialist
                        self.add_keys(table, [{"paths": d["paths"]}], id=id)

                    """ REMOVE FIELDS PRE CHECKS """
                    if not self.check_done(d, [], [["paths", "isos"]]):
                        #### REMOVE FIELDS
                        self.del_keys(table, [{"paths": {"isos"}}])

                except Exception as e:
                    log.error("Something went wrong while upgrading hypervisors!")
                    log.error(e)
                    exit(1)

        if version == 4:
            for d in data:
                id = d["id"]
                d.pop("id", None)
                try:
                    """CONVERSION FIELDS PRE CHECKS"""
                    # ~ if not self.check_done( d,
                    # ~ [],
                    # ~ []):
                    ##### CONVERSION FIELDS
                    # ~ cfg['field']={}
                    # ~ r.table(table).update(cfg).run(self.conn)

                    """ NEW FIELDS PRE CHECKS """
                    if not self.check_done(d, [["cpu_host_model"]], []):
                        ##### NEW FIELDS
                        self.add_keys(table, [{"cpu_host_model": "host-model"}], id=id)

                    # ''' REMOVE FIELDS PRE CHECKS '''
                    # if not self.check_done(d,
                    #                        [],
                    #                        [['paths', 'isos']]):
                    #     #### REMOVE FIELDS
                    #     self.del_keys(table, [{'paths': {'isos'}}])

                except Exception as e:
                    log.error("Something went wrong while upgrading hypervisors!")
                    log.error(e)
                    exit(1)

        if version == 19:
            hypervisors = [
                h
                for h in list(
                    r.table("hypervisors")
                    .pluck(
                        "id", "hypervisors_pools", {"capabilities": "disk_operations"}
                    )
                    .run(self.conn)
                )
                if h["capabilities"]["disk_operations"]
            ]
            pools = list(r.table("hypervisors_pools").run(self.conn))

            for hp in pools:
                hypervisors_in_pool = [
                    hypervisor["id"]
                    for hypervisor in hypervisors
                    if hp["id"] in hypervisor["hypervisors_pools"]
                ]
                paths = hp["paths"]
                for p in paths:
                    for i, item in enumerate(paths[p]):
                        paths[p][i]["disk_operations"] = hypervisors_in_pool
                r.table("hypervisors_pools").get(hp["id"]).update(
                    {"paths": paths, "enabled": False}
                ).run(self.conn)

        return True

    """
    DOMAINS TABLE UPGRADES
    """

    def domains(self, version):
        table = "domains"
        data = list(r.table(table).run(self.conn))
        log.info("UPGRADING " + table + " VERSION " + str(version))
        if version == 2:
            for d in data:
                id = d["id"]
                d.pop("id", None)

                """ CONVERSION FIELDS PRE CHECKS """
                # ~ try:
                # ~ if not self.check_done( d,
                # ~ [],
                # ~ []):
                ##### CONVERSION FIELDS
                # ~ cfg['field']={}
                # ~ r.table(table).update(cfg).run(self.conn)
                # ~ except Exception as e:
                # ~ log.error('Could not update table '+table+' remove fields for db version '+str(version)+'!')
                # ~ log.error('Error detail: '+str(e))

                """ NEW FIELDS PRE CHECKS """
                try:
                    if not self.check_done(d, ["preferences"], []):
                        ##### NEW FIELDS
                        self.add_keys(
                            table,
                            [
                                {
                                    "options": {
                                        "viewers": {"spice": {"fullscreen": False}}
                                    }
                                }
                            ],
                            id=id,
                        )
                except Exception as e:
                    log.error(
                        "Could not update table "
                        + table
                        + " add fields for db version "
                        + str(version)
                        + "!"
                    )
                    log.error("Error detail: " + str(e))

                """ REMOVE FIELDS PRE CHECKS """
                # ~ try:
                # ~ if not self.check_done( d,
                # ~ [],
                # ~ []):
                #### REMOVE FIELDS
                # ~ self.del_keys(TABLE,[])
                # ~ except Exception as e:
                # ~ log.error('Could not update table '+table+' remove fields for db version '+str(version)+'!')
                # ~ log.error('Error detail: '+str(e))
        if version == 7:
            for d in data:
                id = d["id"]
                d.pop("id", None)

                """ CONVERSION FIELDS PRE CHECKS """
                # ~ try:
                # ~ if not self.check_done( d,
                # ~ [],
                # ~ []):
                ##### CONVERSION FIELDS
                # ~ cfg['field']={}
                # ~ r.table(table).update(cfg).run(self.conn)
                # ~ except Exception as e:
                # ~ log.error('Could not update table '+table+' remove fields for db version '+str(version)+'!')
                # ~ log.error('Error detail: '+str(e))

                """ NEW FIELDS PRE CHECKS """
                try:
                    if not self.check_done(d, ["preferences"], []):
                        ##### NEW FIELDS
                        self.add_keys(
                            table,
                            [{"options": {"viewers": {"id_graphics": "default"}}}],
                            id=id,
                        )
                except Exception as e:
                    log.error(
                        "Could not update table "
                        + table
                        + " add fields for db version "
                        + version
                        + "!"
                    )
                    log.error("Error detail: " + str(e))

        if version == 14:
            self.index_create(table, ["tag"])

        if version == 16:
            try:
                r.table(table).index_create(
                    "wg_mac", r.row["create_dict"]["macs"]["wireguard"]
                ).run(self.conn)
            except:
                None

        if version == 18:
            try:
                domains = r.table(table).with_fields("id", "tag").run(self.conn)
                for d in domains:
                    if d["tag"]:
                        r.table(table).get(d["id"]).update(
                            {"tag": d["tag"].replace("#", "=")}
                        ).run(self.conn)
            except:
                None

        if version == 20:
            domains = r.table(table).with_fields("id", "forced_hyp").run(self.conn)
            for domain in domains:
                if domain["forced_hyp"] and not isinstance(domain["forced_hyp"], list):
                    r.table(table).get(domain["id"]).update(
                        {"forced_hyp": [domain["forced_hyp"]]}
                    ).run(self.conn)
                if domain["forced_hyp"] == ["false"]:
                    r.table(table).get(domain["id"]).update({"forced_hyp": False}).run(
                        self.conn
                    )

        if version == 22:
            try:
                r.table(table).index_create("image_id", r.row["image"]["id"]).run(
                    self.conn
                )
            except:
                None
            try:
                ids = [d["id"] for d in r.table(table).pluck("id").run(self.conn)]
                for domain_id in ids:
                    r.table("domains").get(domain_id).update(
                        {"image": self.get_domain_stock_card(domain_id)}
                    ).run(self.conn)
            except:
                None

        if version == 23:
            r.table(table).filter(r.row["kind"].match("template")).update(
                {"enabled": True}
            ).run(self.conn)

        if version == 24:
            try:
                ids = [
                    d["id"]
                    for d in r.table(table)
                    .filter(~r.row.has_fields("image"))
                    .run(self.conn)
                ]
                for domain_id in ids:
                    r.table("domains").get(domain_id).update(
                        {"image": self.get_domain_stock_card(domain_id)}
                    ).run(self.conn)
            except Exception as e:
                None

        return True

    """
    DEPLOYMENTS TABLE UPGRADES
    """

    def deployments(self, version):
        table = "deployments"
        data = list(r.table(table).run(self.conn))
        log.info("UPGRADING " + table + " VERSION " + str(version))

        if version == 18:
            try:
                deployments = list(r.table(table).run(self.conn))
                for d in deployments:
                    deployment = r.table(table).get(d["id"]).run(self.conn)
                    r.table(table).get(d["id"]).delete().run(self.conn)
                    deployment["id"] = deployment["id"].replace("#", "=")
                    r.table(table).insert(deployment).run(self.conn)
            except:
                None

        return True

    """
    MEDIA TABLE UPGRADES
    """

    def media(self, version):
        table = "media"
        log.info("UPGRADING " + table + " VERSION " + str(version))
        # ~ data=list(r.table(table).run(self.conn))
        if version == 3:
            """KEY INDEX FIELDS PRE CHECKS"""
            self.index_create(table, ["kind"])
        if version == 9:
            """KEY INDEX FIELDS PRE CHECKS"""
            self.index_create(table, ["category", "group"])
            # ~ for d in data:
            # ~ id=d['id']
            # ~ d.pop('id',None)
            # ~ ''' CONVERSION FIELDS PRE CHECKS '''
            # ~ try:
            # ~ if not self.check_done( d,
            # ~ [],
            # ~ []):
            ##### CONVERSION FIELDS
            # ~ cfg['field']={}
            # ~ r.table(table).update(cfg).run(self.conn)
            # ~ except Exception as e:
            # ~ log.error('Could not update table '+table+' remove fields for db version '+str(version)+'!')
            # ~ log.error('Error detail: '+str(e))

            # ~ ''' NEW FIELDS PRE CHECKS '''
            # ~ try:
            # ~ if not self.check_done( d,
            # ~ ['preferences'],
            # ~ []):
            # ~ ##### NEW FIELDS
            # ~ self.add_keys(  table,
            # ~ [   {'options': {'viewers':{'spice':{'fullscreen':False}}}}],
            # ~ id=id)
            # ~ except Exception as e:
            # ~ log.error('Could not update table '+table+' add fields for db version '+str(version)+'!')
            # ~ log.error('Error detail: '+str(e))

            # ~ ''' REMOVE FIELDS PRE CHECKS '''
            # ~ try:
            # ~ if not self.check_done( d,
            # ~ [],
            # ~ []):
            #### REMOVE FIELDS
            # ~ self.del_keys(TABLE,[])
            # ~ except Exception as e:
            # ~ log.error('Could not update table '+table+' remove fields for db version '+str(version)+'!')
            # ~ log.error('Error detail: '+str(e))

        return True

    """
    GROUPS TABLE UPGRADES
    """

    def groups(self, version):
        table = "groups"
        log.info("UPGRADING " + table + " VERSION " + str(version))
        # ~ data=list(r.table(table).run(self.conn))
        if version == 9:
            """KEY INDEX FIELDS PRE CHECKS"""
            self.index_create(table, ["parent_category"])
            # ~ for d in data:
            # ~ id=d['id']
            # ~ d.pop('id',None)
            # ~ ''' CONVERSION FIELDS PRE CHECKS '''
            # ~ try:
            # ~ if not self.check_done( d,
            # ~ [],
            # ~ []):
            ##### CONVERSION FIELDS
            # ~ cfg['field']={}
            # ~ r.table(table).update(cfg).run(self.conn)
            # ~ except Exception as e:
            # ~ log.error('Could not update table '+table+' remove fields for db version '+str(version)+'!')
            # ~ log.error('Error detail: '+str(e))

            # ~ ''' NEW FIELDS PRE CHECKS '''
            # ~ try:
            # ~ if not self.check_done( d,
            # ~ ['preferences'],
            # ~ []):
            #        #~ data=list(r.table(table).run(self.conn))               #~ [   {'options': {'viewers':{'spice':{'fullscreen':False}}}}],
            # ~ id=id)
            # ~ except Exception as e:
            # ~ log.error('Could not update table '+table+' add fields for db version '+str(version)+'!')
            # ~ log.error('Error detail: '+str(e))

            # ~ ''' REMOVE FIELDS PRE CHECKS '''
            # ~ try:
            # ~ if not self.check_done( d,
            # ~ [],
            # ~ []):
            #### REMOVE FIELDS
            # ~ self.del_keys(TABLE,[])
            # ~ except Exception as e:
            # ~ log.error('Could not update table '+table+' remove fields for db version '+str(version)+'!')
            # ~ log.error('Error detail: '+str(e))

        return True

    """
    DOMAINS TABLE VIDEOS
    """

    def videos(self, version):
        table = "videos"
        log.info("UPGRADING " + table + " VERSION " + str(version))
        if version == 12:
            r.table("videos").insert(
                [
                    {
                        "allowed": {
                            "categories": False,
                            "groups": False,
                            "roles": False,
                            "users": False,
                        },
                        "description": "nvidia with qxl only used to install drivers",
                        "heads": 1,
                        "id": "nvidia-with-qxl",
                        "model": "qxl",
                        "name": "NVIDIA with QXL",
                        "ram": 65536,
                        "vram": 65536,
                    },
                    {
                        "allowed": {
                            "categories": False,
                            "groups": False,
                            "roles": False,
                            "users": False,
                        },
                        "description": "Nvidia default profile",
                        "heads": 1,
                        "id": "gpu-default",
                        "model": "nvidia",
                        "name": "gpu-default",
                        "ram": 1048576,
                        "vram": 1048576,
                    },
                ]
            ).run(self.conn)

        return True

    """
    DOMAINS TABLE GRAPHICS
    """

    def graphics(self, version):
        table = "graphics"
        log.info("UPGRADING " + table + " VERSION " + str(version))
        # ~ data=list(r.table(table).run(self.conn))
        if version == 7:
            r.table(table).delete().run(self.conn)
            r.table("graphics").insert(
                [
                    {
                        "id": "default",
                        "name": "Default",
                        "description": "Spice viewer with compression and vlc",
                        "allowed": {
                            "roles": [],
                            "categories": [],
                            "groups": [],
                            "users": [],
                        },
                        "types": {
                            "spice": {
                                "options": {
                                    "image": {"compression": "auto_glz"},
                                    "jpeg": {"compression": "always"},
                                    "playback": {"compression": "off"},
                                    "streaming": {"mode": "all"},
                                    "zlib": {"compression": "always"},
                                },
                            },
                            "vlc": {"options": {}},
                        },
                    }
                ]
            ).run(self.conn)

        return True

    """
    USERS TABLE UPGRADES
    """

    def users(self, version):
        table = "users"
        log.info("UPGRADING " + table + " VERSION " + str(version))
        # ~ data=list(r.table(table).run(self.conn))
        if version == 9:
            """KEY INDEX FIELDS PRE CHECKS"""
            self.index_create(table, ["category"])

            # ~ for d in data:
            # ~ id=d['id']
            # ~ d.pop('id',None)
            # ~ ''' CONVERSION FIELDS PRE CHECKS '''
            # ~ try:
            # ~ if not self.check_done( d,
            # ~ [],
            # ~ []):
            ##### CONVERSION FIELDS
            # ~ cfg['field']={}
            # ~ r.table(table).update(cfg).run(self.conn)
            # ~ except Exception as e:
            # ~ log.error('Could not update table '+table+' remove fields for db version '+str(version)+'!')
            # ~ log.error('Error detail: '+str(e))

            # ~ ''' NEW FIELDS PRE CHECKS '''
            # ~ try:
            # ~ if not self.check_done( d,
            # ~ ['preferences'],
            # ~ []):
            # ~ ##### NEW FIELDS
            # ~ self.add_keys(  table,
            # ~ [   {'options': {'viewers':{'spice':{'fullscreen':False}}}}],
            # ~ id=id)
            # ~ except Exception as e:
            # ~ log.error('Could not update table '+table+' add fields for db version '+str(version)+'!')
            # ~ log.error('Error detail: '+str(e))

            # ~ ''' REMOVE FIELDS PRE CHECKS '''
            # ~ try:
            # ~ if not self.check_done( d,
            # ~ [],
            # ~ []):
            #### REMOVE FIELDS
            # ~ self.del_keys(TABLE,[])
            # ~ except Exception as e:
            # ~ log.error('Could not update table '+table+' remove fields for db version '+str(version)+'!')
            # ~ log.error('Error detail: '+str(e))

        if version == 13:
            # Change False value to empty string of admin photo field
            # to not break golang unmarshal of json
            # backend/isard/user.go
            if (
                not r.table(table)
                .get("local-default-admin-admin")
                .pluck("photo")
                .run(self.conn)
                .get("photo", True)
            ):
                r.table(table).get("local-default-admin-admin").update(
                    {"photo": ""}
                ).run(self.conn)

        if version == 15:
            # We need to do it for all users
            r.table(table).filter({"photo": None}).update({"photo": ""}).run(self.conn)
            r.table(table).filter({"photo": False}).update({"photo": ""}).run(self.conn)
            r.table(table).update({"photo": (r.row["photo"]).default("")}).run(
                self.conn
            )

        if version == 21:
            try:
                r.table(table).index_create(
                    "wg_client_ip", r.row["vpn"]["wireguard"]["Address"]
                ).run(self.conn)
            except:
                log.error(
                    "Could not update table "
                    + table
                    + " index_create for db version "
                    + str(version)
                    + "!"
                )
                log.error("Error detail: " + str(e))

        return True

    """
    ROLES TABLE UPGRADES
    """

    def roles(self, version):
        table = "roles"
        log.info("UPGRADING " + table + " VERSION " + str(version))
        # ~ data=list(r.table(table).run(self.conn))
        if version == 9:
            manager = r.table("roles").get("manager").run(self.conn)
            if manager is None:
                r.table("roles").insert(
                    {
                        "id": "manager",
                        "name": "Manager",
                        "description": "Can manage users, desktops, templates and media in a category",
                        "quota": {
                            "domains": {
                                "desktops": 10,
                                "desktops_disk_max": 40000000,
                                "templates": 2,
                                "templates_disk_max": 40000000,
                                "running": 2,
                                "isos": 2,
                                "isos_disk_max": 5000000,
                            },
                            "hardware": {"vcpus": 6, "memory": 6000000},
                        },  # 6GB
                    }
                ).run(self.conn)
            # ~ for d in data:
            # ~ id=d['id']
            # ~ d.pop('id',None)
            # ~ ''' CONVERSION FIELDS PRE CHECKS '''
            # ~ try:
            # ~ if not self.check_done( d,
            # ~ [],
            # ~ []):
            ##### CONVERSION FIELDS
            # ~ cfg['field']={}
            # ~ r.table(table).update(cfg).run(self.conn)
            # ~ except Exception as e:
            # ~ log.error('Could not update table '+table+' remove fields for db version '+str(version)+'!')
            # ~ log.error('Error detail: '+str(e))

            # ~ ''' NEW FIELDS PRE CHECKS '''
            # ~ try:
            # ~ if not self.check_done( d,
            # ~ ['preferences'],
            # ~ []):
            # ~ ##### NEW FIELDS
            # ~ self.add_keys(  table,
            # ~ [   {'options': {'viewers':{'spice':{'fullscreen':False}}}}],
            # ~ id=id)
            # ~ except Exception as e:
            # ~ log.error('Could not update table '+table+' add fields for db version '+str(version)+'!')
            # ~ log.error('Error detail: '+str(e))

            # ~ ''' REMOVE FIELDS PRE CHECKS '''
            # ~ try:
            # ~ if not self.check_done( d,
            # ~ [],
            # ~ []):
            #### REMOVE FIELDS
            # ~ self.del_keys(TABLE,[])
            # ~ except Exception as e:
            # ~ log.error('Could not update table '+table+' remove fields for db version '+str(version)+'!')
            # ~ log.error('Error detail: '+str(e))

        return True

    """
    INTERFACES TABLE UPGRADES
    """

    def interfaces(self, version):
        table = "interfaces"
        log.info("UPGRADING " + table + " VERSION " + str(version))
        if version == 11:
            wg = r.table(table).get("wireguard").run(self.conn)
            if wg == None:
                r.table(table).insert(
                    [
                        {
                            "allowed": {
                                "categories": False,
                                "groups": False,
                                "roles": ["admin"],
                                "users": False,
                            },
                            "description": "Allows direct access to guest IP",
                            "id": "wireguard",
                            "ifname": "wireguard",
                            "kind": "network",
                            "model": "virtio",
                            "name": "Wireguard VPN",
                            "net": "wireguard",
                            "qos_id": "unlimited",
                        }
                    ]
                ).run(self.conn)
        if version == 16:
            wg = r.table(table).get("wireguard").run(self.conn)
            if wg == None:
                r.table(table).insert(
                    [
                        {
                            "allowed": {
                                "categories": False,
                                "groups": False,
                                "roles": ["admin"],
                                "users": False,
                            },
                            "description": "Allows direct access to guest IP",
                            "id": "wireguard",
                            "ifname": "4095",
                            "kind": "ovs",
                            "model": "virtio",
                            "name": "Wireguard VPN",
                            "net": "4095",
                            "qos_id": "unlimited",
                        }
                    ]
                ).run(self.conn)
            else:
                r.table(table).get("wireguard").update(
                    {"kind": "ovs", "ifname": "4095", "net": "4095"}
                ).run(self.conn)

        if version == 17:
            ifs = list(r.table(table).run(self.conn))
            for interface in ifs:
                if interface["ifname"].startswith("br-"):
                    vlan_id = interface["ifname"].split("br-")[1]

                    r.table(table).get(interface["id"]).update(
                        {"ifname": vlan_id, "kind": "ovs", "net": vlan_id}
                    ).run(self.conn)
            # ~ for d in data:
            # ~ id=d['id']
            # ~ d.pop('id',None)
            # ~ ''' CONVERSION FIELDS PRE CHECKS '''
            # ~ try:
            # ~ if not self.check_done( d,
            # ~ [],
            # ~ []):
            ##### CONVERSION FIELDS
            # ~ cfg['field']={}
            # ~ r.table(table).update(cfg).run(self.conn)
            # ~ except Exception as e:
            # ~ log.error('Could not update table '+table+' remove fields for db version '+str(version)+'!')
            # ~ log.error('Error detail: '+str(e))

            # ~ ''' NEW FIELDS PRE CHECKS '''
            # ~ try:
            # ~ if not self.check_done( d,
            # ~ ['preferences'],
            # ~ []):
            # ~ ##### NEW FIELDS
            # ~ self.add_keys(  table,
            # ~ [   {'options': {'viewers':{'spice':{'fullscreen':False}}}}],
            # ~ id=id)
            # ~ except Exception as e:
            # ~ log.error('Could not update table '+table+' add fields for db version '+str(version)+'!')
            # ~ log.error('Error detail: '+str(e))

            # ~ ''' REMOVE FIELDS PRE CHECKS '''
            # ~ try:
            # ~ if not self.check_done( d,
            # ~ [],
            # ~ []):
            #### REMOVE FIELDS
            # ~ self.del_keys(TABLE,[])
            # ~ except Exception as e:
            # ~ log.error('Could not update table '+table+' remove fields for db version '+str(version)+'!')
            # ~ log.error('Error detail: '+str(e))

        return True

    def remotevpn(self, version):
        table = "remotevpn"
        log.info("UPGRADING " + table + " VERSION " + str(version))

        if version == 21:
            try:
                r.table(table).index_create(
                    "wg_client_ip", r.row["vpn"]["wireguard"]["Address"]
                ).run(self.conn)
            except:
                None

    """
    Upgrade general actions
    """

    def add_keys(self, table, keys, id=False):
        for key in keys:
            if id is False:
                r.table(table).update(key).run(self.conn)
            else:
                r.table(table).get(id).update(key).run(self.conn)

    def del_keys(self, table, keys, id=False):
        log.info("Del keys init")
        for key in keys:
            if id is False:
                r.table(table).replace(r.row.without(key)).run(self.conn)
            else:
                r.table(table).get(id).replace(r.row.without(key)).run(self.conn)

    def check_done(self, dict, must=[], mustnot=[]):
        log.info("Self check init")
        done = False
        # ~ check_done(cfg,['grafana','resources','voucher_access',{'engine':{'api':{'token'}}}],[{'engine':{'carbon'}}])
        for m in must:
            if type(m) is str:
                m = [m]
            if self.keys_exists(dict, m):
                done = True
                # ~ print(str(m)+' exists on dict. ok')
            # ~ else:
            # ~ print(str(m)+' not exists on dict. KO')

        for mn in mustnot:
            log.info(mn)
            if type(mn) is str:
                mn = [mn]
            if not self.keys_exists(dict, mn):
                done = True
                # ~ print(str(mn)+' not exists on dict. ok')
            # ~ else:
            # ~ print(str(mn)+' exists on dict. KO')
        return done

    def keys_exists(self, element, keys):
        """
        Check if *keys (nested) exists in `element` (dict).
        """
        if type(element) is not dict:
            raise AttributeError("keys_exists() expects dict as first argument.")
        if len(keys) == 0:
            raise AttributeError(
                "keys_exists() expects at least two arguments, one given."
            )

        _element = element
        for key in keys:
            log.info(key)
            try:
                _element = _element[key]
            except KeyError:
                return False
        return True

    def index_create(self, table, indexes):

        indexes_ontable = r.table(table).index_list().run(self.conn)
        apply_indexes = [mi for mi in indexes if mi not in indexes_ontable]
        for i in apply_indexes:
            r.table(table).index_create(i).run(self.conn)
            r.table(table).index_wait(i).run(self.conn)

    ## To upgrade to default cards
    def get_domain_stock_card(self, domain_id):
        total = 0
        for i in range(0, len(domain_id)):
            total += total + ord(domain_id[i])
        total = total % 48 + 1
        return self.get_card(str(total) + ".jpg", "stock")

    def get_card(self, card_id, type):
        return {
            "id": card_id,
            "url": "/assets/img/desktops/" + type + "/" + card_id,
            "type": type,
        }
