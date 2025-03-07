import logging
import time

from engine.services.db import (
    MAX_LEN_PREV_STATUS_HYP,
    close_rethink_connection,
    new_rethink_connection,
)
from engine.services.log import log
from rethinkdb import r
from rethinkdb.errors import ReqlNonExistenceError

# def get_hyp_hostnames():
#     """
#     NOT USED
#     :return:
#     """
#     r_conn = new_rethink_connection()
#     rtable = r.table('hypervisors')
#
#     l = list(rtable. \
#              filter({'enabled': True}). \
#              pluck('id', 'hostname'). \
#              run(r_conn))
#     close_rethink_connection(r_conn)
#
#     hyps_hostnames = {d['id']: d['hostname'] for d in l}
#
#     return hyps_hostnames


# def get_hyps_to_test():
#     """
#     NOT USED
#     :return:
#     """
#     r_conn = new_rethink_connection()
#     rtable = r.table('hypervisors')
#
#     l = list(rtable. \
#              filter({'enabled': True, 'status': 'ReadyToStart'}). \
#              pluck('id', 'hostname'). \
#              run(r_conn))
#     close_rethink_connection(r_conn)
#
#     hyps_hostnames = {d['id']: d['hostname'] for d in l}
#
#     return hyps_hostnames


def get_hyps_ready_to_start():
    r_conn = new_rethink_connection()
    rtable = r.table("hypervisors")

    l = list(
        rtable.filter({"enabled": True, "status": "ReadyToStart"})
        .pluck("id", "hostname", "hypervisors_pools")
        .run(r_conn)
    )
    close_rethink_connection(r_conn)

    hyps_hostnames = {d["id"]: d["hostname"] for d in l}

    return hyps_hostnames


def get_hypers_disk_operations():
    r_conn = new_rethink_connection()
    rtable = r.table("hypervisors")

    hypers_ids = [
        d["id"]
        for d in list(
            rtable.filter({"enabled": True, "capabilities": {"disk_operations": True}})
            .pluck("id")
            .run(r_conn)
        )
    ]

    close_rethink_connection(r_conn)

    return hypers_ids

    pass


def update_hyp_thread_status(thread_type, hyp_id, status):

    if thread_type in ["worker", "disk_operations", "long_operations"] and status in [
        "Started",
        "Stopped",
        "Starting",
        "Stopping",
        "Deleting",
    ]:

        r_conn = new_rethink_connection()
        rtable = r.table("hypervisors")
        result = (
            rtable.get(hyp_id)
            .update({"thread_status": {thread_type: status}})
            .run(r_conn)
        )

        if status != "Started":
            d = (
                rtable.get(hyp_id)
                .pluck("thread_status", "status", "capabilities")
                .run(r_conn)
            )
            status_hyp = d["status"]
            if status_hyp == "Online":
                update_hyp_status(
                    hyp_id,
                    "Offline",
                    f"thread {thread_type} is not Started. Status of thread: {status}",
                )
            elif status_hyp == "Deleting":
                ko_disk_operations = False
                if d["capabilities"].get("disk_operations", False) is True:
                    if (
                        d["thread_status"].get("disk_operations", "") == "Stopped"
                        and d["thread_status"].get("long_operations", "") == "Stopped"
                    ):
                        ko_disk_operations = True
                elif d["capabilities"].get("disk_operations", True) is False:
                    ko_disk_operations = True

                ko_worker = False
                if d["capabilities"].get("hypervisor", False) is True:
                    if d["thread_status"].get("worker", "") == "Stopped":
                        ko_worker = True
                elif d["capabilities"].get("hypervisor", True) is False:
                    ko_worker = True

                if ko_worker is True and ko_disk_operations is True:
                    result = rtable.get(hyp_id).delete().run(r_conn)
                    close_rethink_connection(r_conn)
                    return result

        elif status == "Started":
            d = (
                rtable.get(hyp_id)
                .pluck("thread_status", "status", "capabilities")
                .run(r_conn)
            )

            ok_disk_operations = False
            if d["capabilities"].get("disk_operations", False) is True:
                if (
                    d["thread_status"].get("disk_operations", "") == "Started"
                    and d["thread_status"].get("long_operations", "") == "Started"
                ):
                    ok_disk_operations = True
            elif d["capabilities"].get("disk_operations", True) is False:
                ok_disk_operations = True

            ok_worker = False
            if d["capabilities"].get("hypervisor", False) is True:
                if d["thread_status"].get("worker", "") == "Started":
                    ok_worker = True
            elif d["capabilities"].get("hypervisor", True) is False:
                ok_worker = True

            if ok_worker is True and ok_disk_operations is True:
                update_hyp_status(hyp_id, "Online", "all threads for hyp are Started")
        close_rethink_connection(r_conn)
        return result
    else:
        return False


def update_hyp_status(id, status, detail="", uri=""):
    # INFO TO DEVELOPER: TODO debería pillar el estado anterior del hypervisor y ponerlo en un campo,
    # o mejor aún, guardar un histórico con los tiempos de cambios en un diccionario que
    # en python puede ser internamente una cola de X elementos (número de elementos de configuración)
    # como una especie de log de cuando cambio de estado

    # INFO TO DEVELOPER: pasarlo a una función en functions
    defined_status = [
        "Offline",
        #'TryConnection',
        #'ReadyToStart',
        #'StartingThreads',
        "Error",
        "Deleting",
        "Online",
    ]
    #'Blocked',
    #'DestroyingDomains',
    #'StoppingThreads']
    if status == "Error":
        pass
    if status in defined_status:
        r_conn = new_rethink_connection()
        rtable = r.table("hypervisors")
        if len(uri) > 0:
            dict_update = {"status": status, "uri": uri}
        else:
            dict_update = {"status": status}

        d = (
            rtable.get(id)
            .pluck("status", "status_time", "prev_status", "detail")
            .run(r_conn)
        )

        if "status" in d.keys():
            if "prev_status" not in d.keys():
                dict_update["prev_status"] = []

            else:
                if type(d["prev_status"]) is list:
                    dict_update["prev_status"] = d["prev_status"]
                else:
                    dict_update["prev_status"] = []

            d_old_status = {}
            d_old_status["status"] = d["status"]
            if "detail" in d.keys():
                d_old_status["detail"] = d["detail"]
            else:
                d_old_status["detail"] = ""
            if "status_time" in d.keys():
                d_old_status["status_time"] = d["status_time"]

            dict_update["prev_status"].insert(0, d_old_status)
            dict_update["prev_status"] = dict_update["prev_status"][
                :MAX_LEN_PREV_STATUS_HYP
            ]

        now = time.time()
        dict_update["status_time"] = now

        # if len(detail) == 0:
        #     rtable.filter({'id':id}).\
        #           update(dict_update).\
        #           run(r_conn)
        #     # rtable.filter({'id':id}).\
        #     #       replace(r.row.without('detail')).\
        #     #       run(r_conn)
        #     close_rethink_connection(r_conn)
        #
        # else:
        dict_update["detail"] = str(detail)
        rtable.filter({"id": id}).update(dict_update).run(r_conn)
        close_rethink_connection(r_conn)

    else:
        log.error("hypervisor status {} is not defined".format(status))
        return False


def get_id_hyp_from_uri(uri):
    r_conn = new_rethink_connection()
    rtable = r.table("hypervisors")
    l = list(rtable.filter({"uri": uri}).pluck("id").run(r_conn))
    close_rethink_connection(r_conn)
    if len(l) > 0:
        return l[0]["id"]
    else:
        log.error(
            "function: {} uri {} not defined in hypervisors table".format(
                str(__name__), uri
            )
        )


def get_hyp_hostnames_online():
    r_conn = new_rethink_connection()
    rtable = r.table("hypervisors")
    l = list(
        rtable.filter({"enabled": True, "status": "Online"})
        .pluck("id", "hostname")
        .run(r_conn)
    )
    close_rethink_connection(r_conn)
    log.debug(l)
    if len(l) > 0:
        hyps_hostnames = {d["id"]: d["hostname"] for d in l}

        return hyps_hostnames
    else:
        return dict()


# def update_hyp_enable(hyp_id, enable=True):
#     """
#     NOT USED
#     :param hyp_id:
#     :param enable:
#     :return:
#     """
#     r_conn = new_rethink_connection()
#     rtable = r.table('hypervisors')
#     # out={}
#     # for hyp_id in argv:
#     #     o = rtable.get(hyp_id).\
#     #          update({'enabled':enable}).\
#     #          run(r_conn)
#     #     out[hyp_id] = o
#     out = rtable.get(hyp_id). \
#         update({'enabled': enable}). \
#         run(r_conn)
#     close_rethink_connection(r_conn)
#     return out


# def update_hyp_capability(hyp_id, capability, enable=True):
#     """
#     NOT USED
#     :param hyp_id:
#     :param capability:
#     :param enable:
#     :return:
#     """
#     r_conn = new_rethink_connection()
#     rtable = r.table('hypervisors')
#
#     out = rtable.get(hyp_id). \
#         update({'capabilities': {capability: enable}}). \
#         run(r_conn)
#     close_rethink_connection(r_conn)
#     return out


def update_hyp_only_forced(hyp_id, only_forced=True):
    r_conn = new_rethink_connection()
    rtable = r.table("hypervisors")
    if only_forced != True:
        only_forced = False
    out = rtable.get(hyp_id).update({"only_forced": only_forced}).run(r_conn)
    close_rethink_connection(r_conn)
    return out


def update_uri_hyp(hyp_id, uri):
    r_conn = new_rethink_connection()
    rtable = r.table("hypervisors")
    out = rtable.get(hyp_id).update({"uri": uri}).run(r_conn)
    close_rethink_connection(r_conn)
    return out


def get_hyp_status(hyp_id):
    r_conn = new_rethink_connection()
    rtable = r.table("hypervisors")
    try:
        out = rtable.get(hyp_id).pluck("status").run(r_conn)
    except ReqlNonExistenceError:
        close_rethink_connection(r_conn)
        return False

    close_rethink_connection(r_conn)
    return out["status"]


def get_hyp_hostname_from_id(id):
    r_conn = new_rethink_connection()
    try:
        l = r.table("hypervisors").get(id).pluck("hostname", "port", "user").run(r_conn)
        close_rethink_connection(r_conn)
    except ReqlNonExistenceError:
        close_rethink_connection(r_conn)
        return False, False, False
    if len(l) > 0:
        if l.__contains__("user") and l.__contains__("port"):
            return l["hostname"], l["port"], l["user"]
        else:
            log.error(
                "hypervisor {} does not contain user or port in database".format(id)
            )
            return False, False, False
    else:
        return False, False, False


def get_hypers_ids_with_status(status):
    r_conn = new_rethink_connection()
    rtable = r.table("hypervisors")

    l = list(rtable.filter({"status": status}).pluck("id").run(r_conn))
    if len(l) > 0:
        hypers = [d["id"] for d in l]
    else:
        hypers = []
    close_rethink_connection(r_conn)
    return hypers


def get_hypers_enabled_with_capabilities_status():
    r_conn = new_rethink_connection()
    rtable = r.table("hypervisors")

    hypers = list(
        rtable.filter({"enabled": True})
        .pluck("capabilities", "status", "id", "thread_status")
        .run(r_conn)
    )

    close_rethink_connection(r_conn)
    return hypers


def get_max_hyp_number():
    r_conn = new_rethink_connection()
    rtable = r.table("hypervisors")

    hypers = list(rtable.pluck("hypervisor_number").run(r_conn))

    close_rethink_connection(r_conn)
    if len(hypers) == 0:
        return -1
    else:
        return max([d["hypervisor_number"] for d in hypers])


def get_hyp_hostname_user_port_from_id(id):
    r_conn = new_rethink_connection()
    l = r.table("hypervisors").get(id).pluck("hostname", "user", "port").run(r_conn)
    close_rethink_connection(r_conn)

    if len(l) > 0:
        if l.__contains__("user") and l.__contains__("port"):
            return l
        else:
            log.error(
                "hypervisor {} does not contain user or port in database".format(id)
            )
            return False
    else:
        return False


def update_all_hyps_status(reset_status="Offline", reset_thread_status="Stopped"):
    r_conn = new_rethink_connection()
    d_reset_thread_status = {
        "worker": reset_thread_status,
        "long_operations": reset_thread_status,
        "disk_operations": reset_thread_status,
    }
    results = (
        r.table("hypervisors")
        .update({"status": reset_status, "thread_status": d_reset_thread_status})
        .run(r_conn)
    )
    close_rethink_connection(r_conn)
    return results


def get_hyps_with_status(list_status, not_=False, empty=False):
    r_conn = new_rethink_connection()
    rtable = r.table("hypervisors")
    if not_ == True:
        l = list(
            rtable.filter({"enabled": True})
            .filter(lambda d: r.not_(r.expr(list_status).contains(d["status"])))
            .run(r_conn)
        )
    else:
        l = list(
            rtable.filter({"enabled": True})
            .filter(lambda d: r.expr(list_status).contains(d["status"]))
            .run(r_conn)
        )

    if empty == True:
        nostatus = list(
            rtable.filter({"enabled": True})
            .filter(lambda n: ~n.has_fields("status"))
            .run(r_conn)
        )
        l = l + nostatus

    close_rethink_connection(r_conn)
    return l


def update_hypervisor_failed_connection(id, fail_connected_reason=""):
    r_conn = new_rethink_connection()
    rtable = r.table("hypervisors")
    rtable.get(id).update({"detail": str(fail_connected_reason)}).run(r_conn)
    # if len(fail_connected_reason) > 0:
    #     rtable.get(id).update({'detail':fail_connected_reason}).run(r_conn)
    # else:
    #     rtable.get(id).replace(r.row.without('fail_connected_reason')).run(r_conn)
    close_rethink_connection(r_conn)


# def initialize_db_status_hyps():
#     """
#     NOT USED
#     :return:
#     """
#     r_conn = new_rethink_connection()
#     rtable = r.table('hypervisors')
#
#     # all hyps to offline
#     rtable.filter({'enabled': False}). \
#         update({'status': 'Offline'}). \
#         run(r_conn)
#     rtable.filter({'enabled': True}). \
#         update({'status': 'Offline'}). \
#         run(r_conn)
#     # return only enabled
#     l = list(rtable.filter({'enabled': True}). \
#              pluck(['id', 'hostname']).
#              run(r_conn))
#
#     close_rethink_connection(r_conn)
#     if len(l) > 0:
#         hyps_hostnames = {d['id']: d['hostname'] for d in l}
#
#         return hyps_hostnames
#     else:
#         return dict()


# def insert_hyp(id,
#                hostname,
#                enable=True,
#                status='Offline',
#                hypervisors_pools=['default'],
#                user='root',
#                port='22'):
#     """
#     NOT USED
#     :param id:
#     :param hostname:
#     :param enable:
#     :param status:
#     :param hypervisors_pools:
#     :param user:
#     :param port:
#     :return:
#     """
#     r_conn = new_rethink_connection()
#     rtable = r.table('hypervisors')
#
#     rtable.insert({'id': id,
#                    'hostname': hostname,
#                    'enabled': enable,
#                    'status': status,
#                    'hypervisors_pools': pools,
#                    'user': user,
#                    'port': port,
#                    'detail': 'new hypervisor created'}). \
#         run(r_conn)
#     close_rethink_connection(r_conn)


# def add_hypers_to_pool(id_pool, *id_hypers):
#     """
#     NOT USED
#     :param id_pool:
#     :param id_hypers:
#     :return:
#     """
#     r_conn = new_rethink_connection()
#     rtable = r.table('hypervisors')
#     return_operations = []
#     for id_hyp in id_hypers:
#         old_pool = rtable.get(id_hyp).pluck('hypervisors_pools').run(r_conn)
#         if len(old_pool) == 0:
#             pools = [id_pool]
#         else:
#             pools = old_pool['hypervisors_pools']
#         if id_pool not in pools:
#             pools.append(id_pool)
#         return_operations.append(rtable.filter({'id': id_hyp}). \
#                                  update({'hypervisors_pools': pools}). \
#                                  run(r_conn))
#
#     close_rethink_connection(r_conn)
#     return return_operations


# def del_hypers_from_pool(id_pool, *id_hypers):
#     """
#     NOT USED
#     :param id_pool:
#     :param id_hypers:
#     :return:
#     """
#     r_conn = new_rethink_connection()
#     rtable = r.table('hypervisors')
#     return_operations = []
#     for id_hyp in id_hypers:
#         old_pool = rtable.get(id_hyp).pluck('hypervisors_pools').run(r_conn)
#         if len(old_pool) == 0:
#             pools = [id_pool]
#         else:
#             pools = old_pool['hypervisors_pools']
#             if id_pool in pools:
#                 pools.remove(id_pool)
#                 return_operations.append(rtable.filter({'id': id_hyp}). \
#                                          update({'hypervisors_pools': pools}). \
#                                          run(r_conn))
#
#     close_rethink_connection(r_conn)
#     return return_operations


def get_pool_hypers_conf(id_pool="default"):
    r_conn = new_rethink_connection()
    rtable = r.table("hypervisors_pools")

    result = rtable.get(id_pool).run(r_conn)

    close_rethink_connection(r_conn)
    return result


def get_hypers_in_pool(
    id_pool="default", only_online=True, exclude_hyp_only_forced=False
):
    r_conn = new_rethink_connection()
    rtable = r.table("hypervisors")

    l_forced = []
    if exclude_hyp_only_forced is True:
        if only_online:
            l_forced = list(
                rtable.filter(r.row["hypervisors_pools"].contains(id_pool))
                .filter({"status": "Online", "only_forced": True})
                .pluck("id")
                .run(r_conn)
            )
        else:
            l_forced = list(
                rtable.filter(r.row["hypervisors_pools"].contains(id_pool))
                .filter({"only_forced": True})
                .pluck("id")
                .run(r_conn)
            )

    if only_online:
        l = list(
            rtable.filter(r.row["hypervisors_pools"].contains(id_pool))
            .filter({"status": "Online"})
            .pluck("id")
            .run(r_conn)
        )
    else:
        l = list(
            rtable.filter(r.row["hypervisors_pools"].contains(id_pool))
            .pluck("id")
            .run(r_conn)
        )

    hyps_id = [a["id"] for a in l]
    hyps_forced = [a["id"] for a in l_forced]
    removed = [hyps_id.remove(i) for i in hyps_forced]

    close_rethink_connection(r_conn)
    return hyps_id


def get_hypers_info(id_pool="default", pluck=None, exclude_only_forced=False):
    r_conn = new_rethink_connection()
    rtable = r.table("hypervisors")
    l_only_forced = []
    if exclude_only_forced is True:
        if not pluck:
            l_only_forced = list(
                rtable.filter(r.row["hypervisors_pools"].contains(id_pool))
                .filter({"status": "Online", "only_forced": True})
                .run(r_conn)
            )
        else:
            l_only_forced = list(
                rtable.filter(r.row["hypervisors_pools"].contains(id_pool))
                .filter({"status": "Online", "only_forced": True})
                .pluck(pluck)
                .run(r_conn)
            )

    if not pluck:
        l_all = list(
            rtable.filter(r.row["hypervisors_pools"].contains(id_pool))
            .filter({"status": "Online"})
            .run(r_conn)
        )
    else:
        l_all = list(
            rtable.filter(r.row["hypervisors_pools"].contains(id_pool))
            .filter({"status": "Online"})
            .pluck(pluck)
            .run(r_conn)
        )

    results = [a for a in l_all if a["id"] not in [b["id"] for b in l_only_forced]]
    close_rethink_connection(r_conn)
    return results


# def delete_hyp(hyp_id):
#     """
#     NOT USED
#     :param hyp_id:
#     :return:
#     """
#     r_conn = new_rethink_connection()
#     rtable = r.table('hypervisors')
#
#     results = rtable.get(hyp_id).delete().run(r_conn)
#     close_rethink_connection(r_conn)


# def list_all_hyps():
#     """
#     NOT USED
#     :return:
#     """
#     r_conn = new_rethink_connection()
#     rtable = r.table('hypervisors')
#
#     results = rtable.run(r_conn)
#     l = list(results)
#     close_rethink_connection(r_conn)
#     return l


def update_db_hyp_info(id, hyp_info):
    r_conn = new_rethink_connection()
    rtable = r.table("hypervisors")

    rtable.filter({"id": id}).update({"info": hyp_info}).run(r_conn)
    close_rethink_connection(r_conn)


def get_hyp(hyp_id):
    r_conn = new_rethink_connection()
    rtable = r.table("hypervisors")

    out = rtable.get(hyp_id).run(r_conn)
    close_rethink_connection(r_conn)
    return out


def update_db_default_gpu_models(hyp_id, default_gpu_models):
    r_conn = new_rethink_connection()
    rtable = r.table("hypervisors")
    out = (
        rtable.get(hyp_id)
        .update({"default_gpu_models": default_gpu_models})
        .run(r_conn)
    )
    close_rethink_connection(r_conn)
    return out


def update_uids_for_nvidia_id(hyp_id, gpu_id, d_uids):
    r_conn = new_rethink_connection()
    rtable = r.table("hypervisors")
    # out = rtable.get(hyp_id).update({'nvidia_uids': ''}).run(r_conn)
    out = rtable.get(hyp_id).update({"nvidia_uids": {gpu_id: d_uids}}).run(r_conn)
    close_rethink_connection(r_conn)
    return out
