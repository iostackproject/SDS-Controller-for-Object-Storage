from abstract_metric import Metric
from metrics_parser import parse_swift_metrics
class Get_ops_tenant(Metric):
    _sync = {}
    _async = ['get_value', 'attach', 'detach', 'notify', 'start_consuming','stop_consuming', 'init_consum', 'stop_actor']
    _ref = ['attach', 'detach']
    _parallel = []

    def __init__(self, exchange, queue, routing_key, host):
        Metric.__init__(self)

        self.host = host
        self.queue = queue
        self.routing_key = routing_key
        self.name = "get_ops_tenant"
        self.exchange = exchange
        print 'Get ops tenant initialized'

    def notify(self, body):
        """
        PUT VAL swift_mdw/groupingtail-swift_metrics*4f0279da74ef4584a29dc72c835fe2c9*get_ops/counter interval=5.000 1448964179.433:198
        """
        body_parsed = parse_swift_metrics(body)
        try:
            for observer in self._observers[body_parsed.tenant_id]:
                observer.update(self.name, body_parsed)
        except:
            print "fail", body_parsed
            pass



    def get_value(self):
        return self.value

    # def callback(self, ch, method, properties, body):
    #     print 'body', body
    #     self.notify(body)