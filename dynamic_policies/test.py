import sys
import os.path

import dsl_parser as p
import time
import operator
from pyactive.controller import init_host, serve_forever, start_controller, interval, sleep
from pyactive.exception import TimeoutError, PyactiveError
import requests
import json
import signal

# lists = [{"tenant_id":123, "througput":1}, {"tenant_id":3, "througput":1}, {"tenant_id":2, "througput":1},]
# json_lists = json.dumps(lists)
#
# print json_lists
#
# pepito = json.loads(lists)
# for p in pepito:
#     if p["tenant_id"] == 2:
#
# print operator.gt(10, 15)
# print operator.gt(5, 5)
# print operator.gt(10, 3)

# t = Througput("througput")
# s = Slowdown("slowdown")
# # r = p.parse("FOR 2312 WHEN slowdown  > 3 DO compress")
# r = p.parse("FOR 2312 WHEN througput < 3 OR slowdown == 1 AND througput == 5 OR througput == 6 DO action")
#
# print r.asList()
# rule = Rule(r)
# print 'rule created'
# print 'rule', rule.tenant
# t.attach(rule)
# s.attach(rule)
# time.sleep(40)
# t.stop_consuming()

def start_test():
    tcpconf = ('tcp', ('127.0.0.1', 6375))
    momconf = ('mom',{'name':'metric_host','ip':'127.0.0.1','port':61613, 'namespace':'/topic/iostack'})
    global host
    host = init_host(tcpconf)
    global metrics
    metrics = {}
    metrics["get_ops_tenant"] = host.spawn_id("get_ops_tenant", 'metrics.collectd_metric', 'CollectdMetric', ["amq.topic", "get_ops_tenant", "collectd.*.groupingtail.tm.*.get_ops.#"])
    metrics["put_ops_tenant"] = host.spawn_id("put_ops_tenant", 'metrics.collectd_metric', 'CollectdMetric', ["amq.topic", "put_ops_tenant", "collectd.*.groupingtail.tm.*.put_ops.#"])
    metrics["head_ops_tenant"] = host.spawn_id("head_ops_tenant", 'metrics.collectd_metric', 'CollectdMetric', ["amq.topic", "head_ops_tenant", "collectd.*.groupingtail.tm.*.head_ops.#"])
    metrics["get_bw_tenant"] = host.spawn_id("get_bw_tenant", 'metrics.collectd_metric', 'CollectdMetric', ["amq.topic", "get_bw_tenant", "collectd.*.groupingtail.tm.*.get_bw.#"])
    metrics["put_bw_tenant"] = host.spawn_id("put_bw_tenant", 'metrics.collectd_metric', 'CollectdMetric', ["amq.topic", "put_bw_tenant", "collectd.*.groupingtail.tm.*.put_bw.#"])
    metrics["get_ops_container"] = host.spawn_id("get_ops_container", 'metrics.collectd_metric', 'CollectdMetric', ["amq.topic", "get_ops_container", "collectd.*.groupingtail.cm.*.get_ops.#"])
    metrics["put_ops_container"] = host.spawn_id("put_ops_container", 'metrics.collectd_metric', 'CollectdMetric', ["amq.topic", "put_ops_container", "collectd.*.groupingtail.cm.*.put_ops.#"])
    metrics["head_ops_container"] = host.spawn_id("head_ops_container", 'metrics.collectd_metric', 'CollectdMetric', ["amq.topic", "head_ops_container", "collectd.*.groupingtail.cm.*.head_ops.#"])
    metrics["get_bw_container"] = host.spawn_id("get_bw_container", 'metrics.collectd_metric', 'CollectdMetric', ["amq.topic", "get_bw_container", "collectd.*.groupingtail.cm.*.get_bw.#"])
    metrics["put_bw_container"] = host.spawn_id("put_bw_container", 'metrics.collectd_metric', 'CollectdMetric', ["amq.topic", "put_bw_container", "collectd.*.groupingtail.cm.*.put_bw.#"])
    metrics["get_bw_info"] = host.spawn_id("get_bw_info", 'metrics.get_bw_info', 'Get_Bw_Info', ["amq.topic","get_bw_info", "bwdifferentiation.get_bw_info.#"])
    #metrics["get_bw_info"] = host.spawn_id("get_bw_info", 'metrics.get_bw_info', 'Get_Bw_Info', ["amq.topic", "get_bw_info", "collectd.*.groupingtail.tenant_metrics.*.get_disk_stats.#", host])

    # metrics["througput"] = host.spawn_id("througput", 'metrics.througput', 'Througput', ["througput", host])

    # metrics["slowdown"] = host.spawn_id("slowdown", 'metrics.slowdown', 'Slowdown', ["slowdown", host])
    try:
        for metric in metrics.values():
            metric.init_consum()
        # metrics["slowdown"].init_consum()
    except Exception as e:
        print e.args
        for metric in metrics.values():
            print 'metric!', metric
            metric.stop_actor()

    rules = {}
    rules["get_bw"] = host.spawn_id("abstract_enforcement_algorithm", 'rules.rule_bw', 'AbstractEnforcementAlgorithm', ["abstract_enforcement_algorithm"])
    rules["get_bw"].run("get_bw_info")
    # global rules
    # rules = {}
    # rules_string = """\
    # FOR 4f0279da74ef4584a29dc72c835fe2c9 WHEN get_ops_tenant > 4 DO SET compression WITH param1=2
    # FOR 4f0279da74ef4584a29dc72c835fe2c9 WHEN put_ops_tenant > 4 DO SET compression WITH param1=2
    # FOR 4f0279da74ef4584a29dc72c835fe2c9 WHEN head_ops_tenant > 4 DO SET compression WITH param1=2""".splitlines()
    #
#rules_string = """\
#FOR 4f0279da74ef4584a29dc72c835fe2c9 DO SET io_bandwidth WITH bw=2""".splitlines()
    # #
    # # rules_string = ["FOR 4f0279da74ef4584a29dc72c835fe2c9 WHEN througput < 3 OR slowdown == 1 AND througput == 5 OR througput == 6 DO SET 1 WITH param1=2"]
    # # cont = 0
    # #
    # cont = 0
    # for rule in rules_string:
    #     print 'Next rule to parse: '+rule
    #     rules_to_parse = {}
    #     try:
    #         parsed_rule = p.parse(rule)
    #     except Exception as e:
    #         print "The rule: "+rule+"cannot be parsed"
    #         print "Exception message", e
    #     else:
    #         for tenant in parsed_rule.subject:
    #             print 'tenant', tenant
    #             rules_to_parse[tenant] = parsed_rule
    #
    #
    #         for key in rules_to_parse.keys():
    #             print 'rule ', rules_to_parse[key]
    #             rules[cont] =  host.spawn_id(str(cont), 'rule', 'Rule', [rules_to_parse[key], key, host, '127.0.0.1', 6375, 'tcp'])
    #             rules[cont].start_rule()
    #             cont += 1

        # metrics["slowdown"].attach(rules[0])


def main():
    start_controller('pyactive_thread')
    serve_forever(start_test)
    print 'hola'

def main2():
    # export TOKEN=$(curl -d '{"auth":{"tenantName": "service", "passwordCredentials": {"username": "swift", "password": "urv"}}}' -H "Content-type: application/json" http://swift_mdw:5000/v2.0/tokens -s | jq '.access.token.id' | tr -d '"')
    data = {'auth':{'tenantName': 'service', 'passwordCredentials': {'username': 'swift', 'password': 'urv'}}}

    headers={"Content-type":"application/json"}
    resp = requests.get("http://10.30.235.235:5000/v2.0/tokens", data=json.dumps(data), headers=headers)
    print resp

if __name__ == "__main__":
   main()
