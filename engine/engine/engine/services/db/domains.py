import json
import logging
import sys
import time
from copy import deepcopy

import flatten_dict
from engine.config import TRANSITIONAL_STATUS
from engine.services.db import (
    close_rethink_connection,
    create_list_buffer_history_domain,
    new_rethink_connection,
)
from engine.services.db.db import close_rethink_connection, new_rethink_connection
from engine.services.db.domains_status import stop_last_domain_status
from engine.services.log import logs
from rethinkdb import r
from rethinkdb.errors import ReqlNonExistenceError

STATUS_STABLE_DOMAIN_RUNNING = ["Started", "ShuttingDown", "Paused"]
ALL_STATUS_RUNNING = ["Stopping", "Started", "Stopping", "Shutting-down"]
STATUS_TO_UNKNOWN = ["Started", "Paused", "Shutting-down", "Stopping", "Unknown"]
STATUS_TO_STOPPED = ["Starting", "CreatingTemplate"]
STATUS_FROM_CAN_START = ["Stopped", "Failed"]
STATUS_TO_FAILED = ["Started", "Stopping", "Shutting-down"]

DEBUG_CHANGES = True if logs.changes.handlers[0].level <= 10 else False
if DEBUG_CHANGES:
    import inspect
    import threading


def dict_merge(a, b):
    """recursively merges dict's. not just simple a['key'] = b['key'], if
    both a and bhave a key who's value is a dict then dict_merge is called
    on both values and the result stored in the returned dictionary."""
    if not isinstance(b, dict):
        return b
    result = deepcopy(a)
    for k, v in b.items():
        if k in result and isinstance(result[k], dict):
            result[k] = dict_merge(result[k], v)
        else:
            result[k] = deepcopy(v)
    return result


def delete_domain(id):
    r_conn = new_rethink_connection()
    rtable = r.table("domains")
    results = rtable.get(id).delete().run(r_conn)
    close_rethink_connection(r_conn)
    return results


def update_domain_progress(id_domain, percent):
    r_conn = new_rethink_connection()
    rtable = r.table("domains")
    results = (
        rtable.get(id_domain)
        .update({"progress": {"percent": percent, "when": time.time()}})
        .run(r_conn)
    )
    close_rethink_connection(r_conn)
    return results


def update_domain_force_update(id_domain, true_or_false=False):
    r_conn = new_rethink_connection()
    rtable = r.table("domains")

    results = (
        rtable.get_all(id_domain, index="id")
        .update({"force_update": true_or_false})
        .run(r_conn)
    )

    close_rethink_connection(r_conn)
    return results


def update_domain_forced_hyp(id_domain, hyp_id=None):
    r_conn = new_rethink_connection()
    rtable = r.table("domains")

    if hyp_id:
        forced_hyp = [hyp_id]
    else:
        forced_hyp = False

    results = (
        rtable.get_all(id_domain, index="id")
        .update({"forced_hyp": forced_hyp})
        .run(r_conn)
    )

    close_rethink_connection(r_conn)
    return results


def update_domain_parents(id_domain):
    r_conn = new_rethink_connection()
    rtable = r.table("domains")
    d = rtable.get(id_domain).pluck({"create_dict": "origin"}, "parents").run(r_conn)

    if "parents" not in d.keys():
        parents_with_new_origin = []
    elif type(d["parents"]) is not list:
        parents_with_new_origin = []
    else:
        parents_with_new_origin = d["parents"].copy()

    if "origin" in d["create_dict"].keys():
        parents_with_new_origin.append(d["create_dict"]["origin"])
        results = (
            rtable.get_all(id_domain, index="id")
            .update({"parents": parents_with_new_origin})
            .run(r_conn)
        )

    close_rethink_connection(r_conn)
    return results


def update_domain_status(status, id_domain, hyp_id=None, detail="", keep_hyp_id=False):
    r_conn = new_rethink_connection()
    rtable = r.table("domains")

    if DEBUG_CHANGES:
        thread_name = threading.currentThread().name
        parents = []
        for i in inspect.stack():
            if len(i) > 3:
                p = i[3]
                if p not in [
                    "<module>",
                    "eval_in_context",
                    "evaluate_expression",
                    "do_it",
                    "process_internal_commands",
                    "_do_wait_suspend",
                    "do_wait_suspend",
                    "do_wait_suspend",
                    "trace_dispatch",
                ]:
                    parents.append(p)
        s_parents = " <- ".join(parents)
        logs.changes.debug(
            f"*** update domain {id_domain} to {status}:\n *** {thread_name} - {s_parents}"
        )

    logs.main.debug(
        f"Update domain status -> status: {status} / domain:{id_domain} / hyp_id={hyp_id} / keep_hyp_id?{keep_hyp_id}"
    )
    # INFO TO DEVELOPER TODO: verificar que el estado que te ponen es realmente un estado válido
    # INFO TO DEVELOPER TODO: si es stopped puede interesar forzar resetear hyp_started no??
    # INFO TO DEVELOPER TODO: MOLARÍA GUARDAR UN HISTÓRICO DE LOS ESTADOS COMO EN HYPERVISORES

    # INFO TO DEVELOPER: OJO CON hyp_started a None... peligro si alguien lo chafa, por eso estos if/else

    if keep_hyp_id == True:
        hyp_id = rtable.get(id_domain).pluck("hyp_started").run(r_conn)["hyp_started"]

    if hyp_id is None:
        # print('ojojojo')rtable.get(id_domain)
        results = (
            rtable.get_all(id_domain, index="id")
            .update({"status": status, "hyp_started": "", "detail": json.dumps(detail)})
            .run(r_conn)
        )
    else:
        results = (
            rtable.get_all(id_domain, index="id")
            .update(
                {"hyp_started": hyp_id, "status": status, "detail": json.dumps(detail)}
            )
            .run(r_conn)
        )

    if status == "Stopped":
        stop_last_domain_status(id_domain)
        remove_fieds_when_stopped(id_domain, conn=r_conn)

    close_rethink_connection(r_conn)
    # if results_zero(results):
    #
    #     logs.main.debug('id_domain {} in hyperviros {} does not exist in domain table'.format(id_domain,hyp_id))

    return results


def update_domain_hw_stats(hw_stats, id_domain):
    r_conn = new_rethink_connection()
    rtable = r.table("domains")
    results = rtable.get(id_domain).update({"hw_stats": hw_stats}).run(r_conn)
    return results


def update_domain_hyp_started(domain_id, hyp_id, detail="", status="Started"):
    results = update_domain_status(status, domain_id, hyp_id, detail=detail)
    return results


def update_domain_hyp_stopped(id_domain, status="Stopped"):
    hyp_id = get_domain_hyp_started(id_domain)
    results = update_domain_status(status, id_domain, hyp_id)
    return results


# def start_all_domains_from_user(user):
#     """
#     NOT USED
#     :param user:
#     :return:
#     """
#     l = get_domains_from_user(user)
#     for d in l:
#         domain_id = d['id']
#         if get_domain_status(domain_id) == 'Stopped':
#             update_domain_status('Starting', domain_id)


# def stop_all_domains_from_user(user):
#     """
#     NOT USED
#     :param user:
#     :return:
#     """
#     l = get_domains_from_user(user)
#     for d in l:
#         domain_id = d['id']
#         if get_domain_status(domain_id) == 'Started':
#             update_domain_status('Stopping', domain_id)


def update_all_domains_status(reset_status="Stopped", from_status=ALL_STATUS_RUNNING):
    r_conn = new_rethink_connection()
    if from_status is None:
        results = r.table("domains").update({"status": reset_status}).run(r_conn)

    for initial_status in from_status:
        results = (
            r.table("domains")
            .get_all(initial_status, index="status")
            .update({"status": reset_status})
            .run(r_conn)
        )
    close_rethink_connection(r_conn)
    return results


def get_domain_kind(id_domain):
    r_conn = new_rethink_connection()
    rtable = r.table("domains")
    results = rtable.get(id_domain).pluck("kind").run(r_conn)
    close_rethink_connection(r_conn)
    if results is None:
        return ""

    return results["kind"]


def get_domain_hyp_started(id_domain):
    r_conn = new_rethink_connection()
    rtable = r.table("domains")
    results = rtable.get(id_domain).pluck("hyp_started").run(r_conn)
    close_rethink_connection(r_conn)
    if results is None:
        return ""

    return results["hyp_started"]


def get_custom_dict_from_domain(id_domain):
    r_conn = new_rethink_connection()
    rtable = r.table("domains")
    results = rtable.get(id_domain).pluck("custom").run(r_conn)
    close_rethink_connection(r_conn)
    if results is None:
        return False
    if "custom" not in results.keys():
        return False
    if len(results["custom"]) == 0:
        return False

    return results["custom"]


def update_domain_dict_custom(
    id_domain, id_user, id_category, id_template, mac_address, remote_computer
):
    d_custom = {
        "user": id_user,
        "category": id_category,
        "template": id_template,
        "mac": mac_address,
        "remote_computer": remote_computer,
    }
    r_conn = new_rethink_connection()
    rtable = r.table("domains")
    results = rtable.get(id_domain).update({"custom": d_custom}).run(r_conn)
    close_rethink_connection(r_conn)
    return results


def update_custom_all_dict(id_domain, d_custom):
    r_conn = new_rethink_connection()
    rtable = r.table("domains")
    results = rtable.get(id_domain).update({"custom": d_custom}).run(r_conn)
    close_rethink_connection(r_conn)
    return results


def get_domain_hyp_started_and_status_and_detail(id_domain):
    r_conn = new_rethink_connection()
    rtable = r.table("domains")
    try:
        results = (
            rtable.get(id_domain).pluck("hyp_started", "detail", "status").run(r_conn)
        )
        close_rethink_connection(r_conn)
    except:
        # if results is None:
        return {}
    return results


# def get_domains_with_disks():
#     """
#     NOT USED
#     :return:
#     """
#     r_conn = new_rethink_connection()
#     rtable = r.table('domains')
#     try:
#         l = list(rtable.pluck('id', {'disks_info': ['filename']}).run(r_conn))
#         results = [{'id': d['id'], 'filename': d['disks_info'][0]['filename']} for d in l if 'disks_info' in d.keys()]
#         close_rethink_connection(r_conn)
#     except:
#         # if results is None:
#         close_rethink_connection(r_conn)
#         return []
#     return results


def get_domains_with_status(status):
    """
    get domain with status
    :param status
    :return: list id_domains
    """
    r_conn = new_rethink_connection()
    rtable = r.table("domains")
    try:
        results = rtable.get_all(status, index="status").pluck("id").run(r_conn)
        close_rethink_connection(r_conn)
    except:
        # if results is None:
        close_rethink_connection(r_conn)
        return []
    return [d["id"] for d in results]


def get_domains_with_transitional_status(list_status=TRANSITIONAL_STATUS):
    r_conn = new_rethink_connection()
    rtable = r.table("domains")
    # ~ l = list(rtable.filter(lambda d: r.expr(list_status).
    # ~ contains(d['status'])).pluck('status', 'id', 'hyp_started').
    # ~ run
    l = list(
        rtable.get_all(r.args(list_status), index="status")
        .pluck("status", "id", "hyp_started")
        .run(r_conn)
    )
    close_rethink_connection(r_conn)
    return l


def get_domains_with_status_in_list(list_status=["Started"]):
    r_conn = new_rethink_connection()
    rtable = r.table("domains")
    # ~ l = list(rtable.filter(lambda d: r.expr(list_status).
    # ~ contains(d['status'])).pluck('status', 'id', 'hyp_started').
    # ~ run
    l = list(
        rtable.get_all(r.args(list_status), index="status")
        .pluck("status", "id", "hyp_started")
        .run(r_conn)
    )
    close_rethink_connection(r_conn)
    return l


# def change_status_to_all_domains_with_status(oldstatus, newstatus):
#     """
#     NOT USED
#     :param oldstatus:
#     :param newstatus:
#     :return:
#     """
#     r_conn = new_rethink_connection()
#     rtable = r.table('domains')
#     try:
#         results = rtable.get_all(oldstatus, index='status').pluck('id').run(r_conn)
#         result = rtable.get_all(oldstatus, index='status').update({'status': newstatus}).run(r_conn)
#         close_rethink_connection(r_conn)
#
#     except:
#         # if results is None:
#         close_rethink_connection(r_conn)
#         return []
#     return [d['id'] for d in results]


def update_domain_dict_create_dict(id, create_dict):
    r_conn = new_rethink_connection()
    rtable = r.table("domains")
    results = rtable.get(id).update({"create_dict": create_dict}).run(r_conn)
    close_rethink_connection(r_conn)
    return results


def update_domain_dict_hardware(id, domain_dict, xml=False):
    r_conn = new_rethink_connection()
    rtable = r.table("domains")

    if xml is False:
        results = rtable.get(id).update({"hardware": domain_dict}).run(r_conn)

    else:
        results = (
            rtable.get(id).update({"hardware": domain_dict, "xml": xml}).run(r_conn)
        )

    # if results_zero(results):
    #     logs.main.debug('id_domain {} does not exist in domain table'.format(id))

    close_rethink_connection(r_conn)
    return results


def remove_domain_viewer_values(id):
    r_conn = new_rethink_connection()
    rtable = r.table("domains")

    results = rtable.get(id).replace(r.row.without("viewer")).run(r_conn)
    close_rethink_connection(r_conn)
    return results


def update_disk_backing_chain(
    id_domain,
    index_disk,
    path_disk,
    list_backing_chain,
    new_template=False,
    list_backing_chain_template=[],
):
    r_conn = new_rethink_connection()
    rtable = r.table("domains")
    domain = rtable.get(id_domain).run(r_conn)

    if new_template == True:
        domain["create_dict"]["template_dict"][
            "disks_info"
        ] = list_backing_chain_template

    domain["disks_info"] = list_backing_chain
    results = rtable.replace(domain).run(r_conn)

    #
    # if new_template == True:
    #     dict_disks = rtable.get(id_domain).pluck({'create_dict':{'template_dict':{'hardware':{'disks':{'file':True}}}}}).run(r_conn)['create_dict']['template_dict]']
    # else:
    #     dict_disks = rtable.get(id_domain).pluck({'hardware':{'disks':{'file':True}}}).run(r_conn)
    #
    #
    # if path_disk == dict_disks['hardware']['disks'][index_disk]['file']:
    #     # INFO TO DEVELOPER: BACKING CHAIN NOT IN HARDWARE DICT
    #     # dict_disks['template_json']['hardware']['disks'][index_disk]['backing_chain'] = list_backing_chain
    #     if 'disks_info' not in dict_disks.keys():
    #         dict_disks['disks_info']={}
    #     dict_disks['disks_info']['path_disk'] = list_backing_chain
    #
    #     if new_template == True:
    #         results = rtable.get(id_domain).update({'template_json':dict_disks}).run(r_conn)
    #     else:
    #         results = rtable.get(id_domain).update(dict_disks).run(r_conn)

    close_rethink_connection(r_conn)
    return results

    # else:
    #     logs.main.error('update_disk_backing_chain FAILED: there is not path {} in disk_index {} in domain {}'.format(path_disk,index_disk,id_domain))
    #     return


def update_disk_template_created(id_domain, index_disk):
    r_conn = new_rethink_connection()
    rtable = r.table("domains")
    dict_disk_templates = (
        rtable.get(id_domain).pluck("disk_template_created").run(r_conn)
    )
    dict_disk_templates["disk_template_created"][index_disk] = 1
    results = rtable.get(id_domain).update(dict_disk_templates).run(r_conn)
    close_rethink_connection(r_conn)
    return results


def remove_disk_template_created_list_in_domain(id_domain):
    r_conn = new_rethink_connection()
    rtable = r.table("domains")
    results = (
        rtable.get(id_domain)
        .replace(r.row.without("disk_template_created"))
        .run(r_conn)
    )
    close_rethink_connection(r_conn)
    return results


def update_origin_and_parents_to_new_template(id_domain, template_id):
    r_conn = new_rethink_connection()
    rtable = r.table("domains")
    new_create_dict_origin = {"create_dict": {"origin": template_id}}
    results = rtable.get(id_domain).update(new_create_dict_origin).run(r_conn)
    close_rethink_connection(r_conn)
    return results


def remove_dict_new_template_from_domain(id_domain):
    r_conn = new_rethink_connection()
    rtable = r.table("domains")
    results = (
        rtable.get(id_domain)
        .replace(r.row.without({"create_dict": "template_dict"}))
        .run(r_conn)
    )
    close_rethink_connection(r_conn)
    return results


def get_if_all_disk_template_created(id_domain):
    r_conn = new_rethink_connection()
    rtable = r.table("domains")
    dict_disk_templates = (
        rtable.get(id_domain).pluck("disk_template_created").run(r_conn)
    )
    created = len(dict_disk_templates["disk_template_created"]) == sum(
        dict_disk_templates["disk_template_created"]
    )
    close_rethink_connection(r_conn)
    return created


def create_disk_template_created_list_in_domain(id_domain):
    dict_domain = get_domain(id_domain)
    created_disk_finalished_list = [
        0 for a in range(len(dict_domain["hardware"]["disks"]))
    ]

    r_conn = new_rethink_connection()
    rtable = r.table("domains")
    results = (
        rtable.get(id_domain)
        .update({"disk_template_created": created_disk_finalished_list})
        .run(r_conn)
    )
    close_rethink_connection(r_conn)
    return results


def set_unknown_domains_not_in_hyps(hyps):
    # find domains in status Started,Paused,Unknown
    # that are not in hypervisors
    r_conn = new_rethink_connection()
    rtable = r.table("domains")

    l = list(
        rtable.filter(lambda d: r.expr(STATUS_TO_UNKNOWN).contains(d["status"]))
        .filter(lambda d: r.not_(r.expr(hyps).contains(d["hyp_started"])))
        .update({"status": "Unknown"})
        .run(r_conn)
    )

    l = list(
        rtable.filter(lambda d: r.expr(STATUS_TO_STOPPED).contains(d["status"]))
        .filter(lambda d: r.not_(r.expr(hyps).contains(d["hyp_started"])))
        .update({"status": "Stopped"})
        .run(r_conn)
    )
    close_rethink_connection(r_conn)
    return l


def get_pool_from_domain(domain_id):
    r_conn = new_rethink_connection()
    rtable = r.table("domains")
    try:
        d = rtable.get(domain_id).pluck("hypervisors_pools").run(r_conn)
        if len(d) > 0:
            if len(d["hypervisors_pools"]) > 0:
                pool = d["hypervisors_pools"][0]
            else:
                logs.main.error(
                    f"domain: {domain_id} with not hypervisors_pools in list. Pool default forced."
                )
                pool = "default"
        else:
            logs.main.error(
                f"domain: {domain_id} withouth hypervisors_pools key defined. Pool default forced."
            )
            pool = "default"
    except r.ReqlNonExistenceError:
        logs.main.error(
            "domain_id {} does not exist in domains table".format(domain_id)
        )
        logs.main.debug("function: {}".format(sys._getframe().f_code.co_name))
        pool = "default"

    close_rethink_connection(r_conn)
    return pool


def get_domain_force_update(domain_id):
    r_conn = new_rethink_connection()
    rtable = r.table("domains")

    results = list(
        rtable.get_all(domain_id, index="id").pluck("force_update").run(r_conn)
    )

    close_rethink_connection(r_conn)

    # id_domain doesn't exist
    if len(results) == 0:
        return False

    # force hyp doesn't exist as key in domain dict
    if len(results[0]) == 0:
        return False

    if results[0]["force_update"] is True:
        return True
    else:
        return False


def get_domain_forced_hyp(id_domain):
    r_conn = new_rethink_connection()
    rtable = r.table("domains")

    try:
        d = rtable.get(id_domain).pluck("forced_hyp", "preferred_hyp").run(r_conn)
        close_rethink_connection(r_conn)
    except:
        return False, False
    forced_hyp = d.get("forced_hyp", False)
    preferred_hyp = d.get("preferred_hyp", False)
    ## By now, even the webapp will update it as a list, only lets
    ## to set one forced_hyp
    if forced_hyp:
        forced_hyp = forced_hyp[0]
    else:
        forced_hyp = False
    if isinstance(preferred_hyp, list) and len(preferred_hyp) > 0:
        ## By now, even the webapp will update it as a list, only lets
        ## to set one forced_hyp
        if preferred_hyp[0] == "false":
            preferred_hyp = False
    elif preferred_hyp == "false":
        preferred_hyp = False
    return forced_hyp, preferred_hyp


def get_domain(id):
    r_conn = new_rethink_connection()
    rtable = r.table("domains")

    dict_domain = rtable.get(id).run(r_conn)
    close_rethink_connection(r_conn)
    return dict_domain


def get_domain_hardware_dict(id_domain):
    r_conn = new_rethink_connection()
    rtable = r.table("domains")

    result = rtable.get(id_domain).pluck("hardware").run(r_conn)
    close_rethink_connection(r_conn)
    return result["hardware"]


def get_create_dict(id_domain):
    r_conn = new_rethink_connection()
    rtable = r.table("domains")

    result = rtable.get(id_domain).pluck("create_dict").run(r_conn)
    close_rethink_connection(r_conn)
    return result["create_dict"]


def get_domain_status(id):
    r_conn = new_rethink_connection()
    rtable = r.table("domains")

    try:
        domain_status = rtable.get(id).pluck("status").run(r_conn)
    except ReqlNonExistenceError:
        close_rethink_connection(r_conn)
        return None

    close_rethink_connection(r_conn)
    return domain_status["status"]


def get_if_delete_after_stop(id_domain):
    r_conn = new_rethink_connection()
    rtable = r.table("domains")

    try:
        domain_status = rtable.get(id).pluck("delete_after_stopped").run(r_conn)
    except ReqlNonExistenceError:
        close_rethink_connection(r_conn)
        return False

    close_rethink_connection(r_conn)
    if domain_status["delete_after_stopped"] is True:
        return True
    else:
        return False


def get_disks_all_domains():
    r_conn = new_rethink_connection()
    rtable = r.table("domains")

    domains_info_disks = rtable.pluck("id", {"hardware": [{"disks": ["file"]}]}).run(
        r_conn
    )

    tuples_id_disk = [
        (d["id"], d["hardware"]["disks"][0]["file"])
        for d in domains_info_disks
        if "hardware" in d.keys()
    ]

    close_rethink_connection(r_conn)
    return tuples_id_disk


def get_domains(user, status=None, origin=None):
    """

    :param user:
    :param status:
    :return:
    """
    r_conn = new_rethink_connection()
    rtable = r.table("domains")
    obj = {"user": user}
    if status:
        obj["status"] = status
    if origin:
        obj["create_dict"] = {"origin": origin}
    results = rtable.filter(obj).run(r_conn)
    results = list(results)
    close_rethink_connection(r_conn)
    return results


def get_domains_count(user, status=None, origin=None):
    """

    :param user:
    :param status:
    :return:
    """
    r_conn = new_rethink_connection()
    rtable = r.table("domains")
    obj = {"user": user}
    if status:
        obj["status"] = status
    if origin:
        obj["create_dict"] = {"origin": origin}
    result = rtable.filter(obj).count().run(r_conn)
    close_rethink_connection(r_conn)
    return result


# def exist_domain(id):
#     """
#     NOT USED
#     :param id:
#     :return:
#     """
#     r_conn = new_rethink_connection()
#     rtable = r.table('domains')
#
#     l = list(rtable.get(id).run(r_conn))
#     close_rethink_connection(r_conn)
#     if len(l) > 0:
#         return True
#     else:
#         return False


def insert_domain(dict_domain):
    r_conn = new_rethink_connection()
    rtable = r.table("domains")

    result = rtable.insert(dict_domain).run(r_conn)
    close_rethink_connection(r_conn)
    return result


def remove_domain(id):
    r_conn = new_rethink_connection()
    rtable = r.table("domains")

    result = rtable.get(id).delete().run(r_conn)
    close_rethink_connection(r_conn)
    return result


def get_domains_flag_server_to_starting():
    r_conn = new_rethink_connection()
    rtable = r.table("domains")
    try:
        l = list(
            rtable.get_all("desktop", index="kind")
            .filter({"create_dict": {"server": True}})
            .pluck("id", "status")
            .run(r_conn)
        )
    except Exception as e:
        logs.exception_id.debug("0040")
        logs.main.error(e)
        return []
    ids_servers_must_start = [
        d["id"] for d in l if d["status"] in STATUS_FROM_CAN_START
    ]
    close_rethink_connection(r_conn)
    return ids_servers_must_start


def update_domain_history_from_id_domain(domain_id, new_status, new_detail, date_now):
    r_conn = new_rethink_connection()
    rtable = r.table("domains")

    # domain_fields = rtable.get(domain_id).pluck('status','history_domain','detail','hyp_started').run(r_conn)
    try:
        domain_fields = (
            rtable.get(domain_id).pluck("history_domain", "hyp_started").run(r_conn)
        )
    except Exception as e:
        logs.exception_id.debug("0041")
        logs.main.error(
            f"domain {domain_id} does not exists in db and update_domain_history_from_id_domain is not posible"
        )
        logs.main.error(e)
        return False
    close_rethink_connection(r_conn)

    if "history_domain" in domain_fields:
        history_domain = domain_fields["history_domain"]
    else:
        history_domain = []

    if new_detail is None:
        new_detail = ""

    if "hyp_started" in domain_fields:
        hyp_started = domain_fields["hyp_started"]
    else:
        hyp_started = ""

    # now = date_now.strftime("%Y-%b-%d %H:%M:%S.%f")
    now = time.time()
    update_domain_history_status(
        domain_id=domain_id,
        new_status=new_status,
        when=now,
        history_domain=history_domain,
        detail=new_detail,
        hyp_id=hyp_started,
    )


def update_domain_history_status(
    domain_id, new_status, when, history_domain, detail="", hyp_id=""
):
    list_history_domain = create_list_buffer_history_domain(
        new_status, when, history_domain, detail, hyp_id
    )

    r_conn = new_rethink_connection()
    rtable = r.table("domains")
    results = (
        rtable.get(domain_id)
        .update({"history_domain": list_history_domain, "accessed": int(when)})
        .run(r_conn)
    )

    close_rethink_connection(r_conn)
    return results


def get_history_domain(domain_id):
    r_conn = new_rethink_connection()
    rtable = r.table("domains")
    result = rtable.get(domain_id).pluck("history_domain").run(r_conn)
    results = list(result["history_domain"])
    close_rethink_connection(r_conn)
    return results


def get_domain_spice(id_domain):
    r_conn = new_rethink_connection()
    rtable = r.table("domains")
    domain = rtable.get(id).run(r_conn)
    close_rethink_connection(r_conn)
    if "viewer" not in domain.keys():
        return False
    if "tlsport" not in domain["viewer"].keys():
        domain["viewer"]["tlsport"] = False
    if "port" not in domain["viewer"].keys():
        domain["viewer"]["port"] = False
    return {
        "hostname": domain["viewer"]["hostname"],
        "kind": domain["hardware"]["graphics"]["type"],
        "port": domain["viewer"]["port"],
        "tlsport": domain["viewer"]["tlsport"],
        "passwd": domain["viewer"]["passwd"],
    }


def get_domains_from_group(group, kind="desktop"):
    r_conn = new_rethink_connection()
    rtable = r.table("domains")
    l = list(
        r.table("domains")
        .eq_join("user", r.table("users"))
        .without({"right": "id"})
        .without({"right": "kind"})
        .zip()
        .filter({"group": group, "kind": kind})
        .order_by("id")
        .pluck("status", "id", "kind", {"hardware": [{"disks": ["file"]}]})
        .run(r_conn)
    )
    close_rethink_connection(r_conn)
    return [
        {
            "kind": s["kind"],
            "id": s["id"],
            "status": s["status"],
            "disk": s["hardware"]["disks"][0]["file"],
        }
        for s in l
    ]


def get_all_domains_with_id_and_status(status=None, kind="desktop"):
    r_conn = new_rethink_connection()
    rtable = r.table("domains")
    if status is None:
        l = list(rtable.filter({"kind": kind}).pluck("id", "status").run(r_conn))
    else:
        l = list(
            rtable.filter({"kind": kind, "status": status})
            .pluck("id", "status")
            .run(r_conn)
        )
    close_rethink_connection(r_conn)
    return l


def get_all_domains_with_hyp_started(hyp_started_id):
    r_conn = new_rethink_connection()
    rtable = r.table("domains")
    l = list(
        rtable.filter({"hyp_started": hyp_started_id})
        .pluck("id", "status", "hyp_started")
        .run(r_conn)
    )
    close_rethink_connection(r_conn)
    return l


def get_all_domains_with_id_status_hyp_started(status=None, kind="desktop"):
    r_conn = new_rethink_connection()
    rtable = r.table("domains")
    if status is None:
        l = list(
            rtable.filter({"kind": kind})
            .pluck("id", "status", "hyp_started")
            .run(r_conn)
        )
    else:
        l = list(
            rtable.filter({"kind": kind, "status": status})
            .pluck("id", "status", "hyp_started")
            .run(r_conn)
        )
    close_rethink_connection(r_conn)
    return l


def get_domains_from_user(user, kind="desktop"):
    r_conn = new_rethink_connection()
    rtable = r.table("domains")
    l = list(
        rtable.filter({"user": user, "kind": kind})
        .pluck("status", "id", "kind", {"hardware": [{"disks": ["file"]}]})
        .run(r_conn)
    )
    close_rethink_connection(r_conn)
    return [
        {
            "kind": s["kind"],
            "id": s["id"],
            "status": s["status"],
            "disk": s["hardware"]["disks"][0]["file"],
        }
        for s in l
    ]


def get_domains_id(user, id_pool, kind="desktop", origin=None):
    r_conn = new_rethink_connection()
    rtable = r.table("domains")
    # TODO: filter also by pool
    obj = {"user": user, "kind": kind}
    if origin:
        obj["create_dict"] = {"origin": origin}
    l = list(rtable.filter(obj).pluck("id").run(r_conn))
    close_rethink_connection(r_conn)
    ids = [d["id"] for d in l]
    return ids


def update_domain_delete_after_stopped(id_domain, do_delete=True):
    r_conn = new_rethink_connection()
    rtable = r.table("domains")

    rtable.get(id_domain).update({"delete_after_stopped": do_delete}).run(r_conn)
    close_rethink_connection(r_conn)


def update_domain_start_after_created(id_domain, do_create=True):
    r_conn = new_rethink_connection()
    rtable = r.table("domains")

    rtable.get(id_domain).update({"start_after_created": do_create}).run(r_conn)
    close_rethink_connection(r_conn)


def update_domain_createing_template(
    id_domain, template_field, status="CreatingTemplate"
):
    r_conn = new_rethink_connection()
    rtable = r.table("domains")

    rtable.get(id_domain).update(
        {"template_json": template_field, "status": status}
    ).run(r_conn)
    close_rethink_connection(r_conn)


####################################################################
# CLEAN STATUS


def update_domains_started_in_hyp_to_unknown(hyp_id):
    # TODO, ASEGURARNOS QUE LOS status DE LOS DOMINIOS ESTÁN EN start,unknown,paused
    # no deberían tener hypervisor activo en otro estado, pero por si las moscas
    # y ya de paso quitar eh hyp_started si queda alguno
    r_conn = new_rethink_connection()
    rtable = r.table("domains")

    result = (
        rtable.get_all(hyp_id, index="hyp_started")
        .update({"status": "Unknown"})
        .run(r_conn)
    )
    close_rethink_connection(r_conn)
    return result


def update_info_nvidia_hyp_domain(status, nvidia_uid, hyp_id, dom_id=False):
    """status: created,started,stopped,removed"""
    if status not in ["created", "reserved", "started", "stopped", "removed"]:
        return False
    r_conn = new_rethink_connection()
    # rtable_dom = r.table('domains')
    rtable_hyp = r.table("hypervisors")
    if type(nvidia_uid) is not list:
        nvidia_uids = [nvidia_uid]
    else:
        nvidia_uids = nvidia_uid
    # d_hyp = dict(rtable_hyp.get(hyp_id).run(r_conn))
    if hyp_id is None:
        print(f"hyp_id is None in update_info_nvidia_hyp_domain")
        return False
    d = dict(rtable_hyp.get(hyp_id).pluck("nvidia_uids").run(r_conn))
    result = False
    if len(d) > 0:
        d_uids = d["nvidia_uids"]
        if len(d_uids) > 0:
            d_uids_flatten = flatten_dict.flatten(d_uids)
            d_update_merged = {}
            for nvidia_uid in nvidia_uids:
                d_update = {}
                l = [i for i in d_uids_flatten if nvidia_uid in i]
                if len(l) > 0:
                    values = l[0]
                    pci_id = values[0]
                    model = values[1]
                    if status in ["started", "reserved"]:
                        d_update = {pci_id: {model: {nvidia_uid: {"started": dom_id}}}}
                    elif status in ["stopped"]:
                        d_update = {
                            pci_id: {
                                model: {
                                    nvidia_uid: {"started": False, "reserved": False}
                                }
                            }
                        }
                    elif status in ["removed"]:
                        d_update = {
                            pci_id: {
                                model: {
                                    nvidia_uid: {
                                        "created": False,
                                        "started": False,
                                        "reserved": False,
                                    }
                                }
                            }
                        }
                    elif status in ["created"]:
                        d_update = {
                            pci_id: {
                                model: {
                                    nvidia_uid: {
                                        "created": True,
                                        "started": False,
                                        "reserved": False,
                                    }
                                }
                            }
                        }
                if len(d_update) > 0:
                    d_update_merged = dict_merge(d_update_merged, d_update)
            if len(d_update_merged) > 0:
                result = (
                    rtable_hyp.get(hyp_id)
                    .update({"nvidia_uids": d_update_merged})
                    .run(r_conn)
                )

    close_rethink_connection(r_conn)
    return result


def domain_stopped_update_nvidia_uids_status(domain_id, hyp_id):
    r_conn = new_rethink_connection()
    rtable_dom = r.table("domains")
    rtable_hyp = r.table("hypervisors")

    d = dict(
        rtable_dom.get(domain_id)
        .pluck({"create_dict": {"hardware": "videos"}})
        .run(r_conn)
    )
    try:
        video = d["create_dict"]["hardware"]["videos"][0]
    except:
        close_rethink_connection(r_conn)
        return False
    result = False
    if video.find("nvidia") == 0 or video.find("gpu_default"):
        d = dict(rtable_hyp.get(hyp_id).pluck("nvidia_uids").run(r_conn))
        if len(d) > 0:
            d_uids = d["nvidia_uids"]
            if len(d_uids) > 0:
                d_uids_flatten = flatten_dict.flatten(d_uids)
                d_update_merged = {}
                d_uids_domains = {
                    k: v for k, v in d_uids_flatten.items() if type(v) is not bool
                }
                nvidia_uids = set(
                    [k[2] for k, v in d_uids_domains.items() if domain_id in v]
                )

                for nvidia_uid in nvidia_uids:
                    d_update = {}
                    l = [i for i in d_uids_flatten if nvidia_uid in i]
                    if len(l) > 0:
                        values = l[0]
                        pci_id = values[0]
                        model = values[1]
                        # status = 'stopped'
                        d_update = {
                            pci_id: {
                                model: {
                                    nvidia_uid: {"started": False, "reserved": False}
                                }
                            }
                        }
                    if len(d_update) > 0:
                        d_update_merged = dict_merge(d_update_merged, d_update)
                if len(d_update_merged) > 0:
                    result = (
                        rtable_hyp.get(hyp_id)
                        .update({"nvidia_uids": d_update_merged})
                        .run(r_conn)
                    )

    close_rethink_connection(r_conn)
    return result


def get_domains_started_in_hyp(hyp_id, only_started=False, only_unknown=False):
    # TODO, ASEGURARNOS QUE LOS status DE LOS DOMINIOS ESTÁN EN start,unknown,paused
    # no deberían tener hypervisor activo en otro estado, pero por si las moscas
    # y ya de paso quitar eh hyp_started si queda alguno
    r_conn = new_rethink_connection()
    rtable = r.table("domains")

    list_domain = list(
        rtable.get_all(hyp_id, index="hyp_started").pluck("id", "status").run(r_conn)
    )

    if only_started is True:
        d = {
            d["id"]: d["status"]
            for d in list_domain
            if d["status"] in STATUS_STABLE_DOMAIN_RUNNING
        }
    elif only_unknown is True:
        d = {d["id"]: d["status"] for d in list_domain if d["status"] in "Unknown"}
    else:
        d = {d["id"]: d["status"] for d in list_domain}

    close_rethink_connection(r_conn)
    return d


def remove_fieds_when_stopped(id_domain, conn=False):
    if conn is False:
        r_conn = new_rethink_connection()
    else:
        r_conn = conn

    r.table("domains").get(id_domain).update(
        {"create_dict": {"personal_vlans": False}}
    ).run(r_conn)

    if conn is False:
        close_rethink_connection(r_conn)


def get_and_update_personal_vlan_id_from_domain_id(
    id_domain, id_interface, range_start, range_end
):
    r_conn = new_rethink_connection()
    user_id = dict(r.table("domains").get(id_domain).pluck("user").run(r_conn))["user"]
    desktops_up = list(
        r.table("domains")
        .get_all(user_id, index="user")
        .filter((r.row["status"] == "Started") | (r.row["status"] == "Shutting-down"))
        .pluck("id")
        .run(r_conn)
    )
    vlan_id = False
    if len(desktops_up) > 0:
        create_dict = (
            r.table("domains")
            .get(desktops_up[0]["id"])
            .pluck("create_dict")
            .run(r_conn)["create_dict"]
        )
        if create_dict.get("personal_vlans", False) is not False:
            if id_interface in create_dict["personal_vlans"].keys():
                tmp_vlan_id = create_dict["personal_vlans"][id_interface]
                if type(tmp_vlan_id) is int:
                    if tmp_vlan_id <= range_end and tmp_vlan_id >= range_start:
                        vlan_id = tmp_vlan_id
                    else:
                        logs.main.error(
                            f"vlan_id {vlan_id} error: vlan_id > {range_end} or vlan_id < {range_start} in domain {id_domain}"
                        )
                else:
                    logs.main.error(
                        f"vlan_id is not int in personal_vlans dict in create_dict for domain: {id_domain}"
                    )

    if vlan_id is False:
        l_all_vlans_active = list(
            r.table("domains")
            .filter({"status": "Started"})
            .filter(
                (r.row["status"] == "Started") | (r.row["status"] == "Shutting-down")
            )
            .filter(~r.row["create_dict"]["personal_vlans"] == False)
            .pluck({"create_dict": "personal_vlans"})
            .run(r_conn)
        )
        a = [
            list(d.get("create_dict", {}).get("personal_vlans", {}).values())
            for d in l_all_vlans_active
        ]
        l = []
        for v in a:
            l = l + v
        set_vlans_active = set([i for i in l if type(i) is int])
        set_vlans_infraestructure = set(
            [
                int(d["net"])
                for d in r.table("interfaces")
                .filter({"kind": "ovs"})
                .pluck("net")
                .run(r_conn)
            ]
        )
        set_all_range_vlans = set(range(range_start, range_end))
        set_vlans_available = (
            set_all_range_vlans - set_vlans_active - set_vlans_infraestructure
        )

        if len(set_vlans_available) > 0:
            vlan_id = min(set_vlans_available)
        else:
            from pprint import pformat

            logs.main.error(f"not vlans available for personal network: {id_interface}")
            logs.main.debug("vlans_active" + pformat(set_vlans_active))
            logs.main.debug("vlans_infraestructure" + pformat(set_vlans_active))
            logs.main.debug("vlans_all_range" + pformat(set_vlans_active))

    r.table("domains").get(id_domain).update(
        {"create_dict": {"personal_vlans": {id_interface: vlan_id}}}
    ).run(r_conn)
    close_rethink_connection(r_conn)
    return vlan_id
