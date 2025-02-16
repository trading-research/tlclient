# auto generated by update_py.py

import tlclient.trader.message_common as message_common
import tlclient.trader.message_market as message_market

from tlclient.linker.constant import NotificationType
from tlclient.linker.fist import Fist
from tlclient.linker.pb_msg import comm_pb
from tlclient.linker.utility import bytify
from tlclient.trader.constant import MsgType

class Gateway(Fist):

    def __init__(self, acc_name, gateway_name, env_name, addr, fist_type):
        Fist.__init__(self, acc_name, fist_type, env_name)
        self.set_master_addr(addr)
        self.create_fist()
        self.gateway_name = gateway_name

        self.set_hb_desc_name(self.gateway_name)

    def init(self, router_name, use_seperate_queue=True):
        self.reg_req(router_name)
        self.reg_sub(router_name)
        self.reg_push(router_name)
        self.router_name = router_name
        self.use_seperate_queue = use_seperate_queue

    def start(self):
        Fist.start(self)
        self.start_heart_beat(self.router_name, 5)

    # --------- utilities for gateway ---------
    #
    def push_connection_status_change(self, connected, err_id=0, err_msg=''):
        # init conn_status
        conn_status = message_common.GatewayConnectionStatus()
        conn_status.fist_type = self.fist_type
        conn_status.fist_name = bytify(self.fist_name)
        conn_status.gateway_name = bytify(self.gateway_name)
        conn_status.connected = connected
        conn_status.err_id = err_id
        conn_status.err_msg = bytify(err_msg)
        self.safe_push(conn_status, MsgType.GTW_CONNECTION)
        # sync status to heartbeat
        self.set_hb_status(comm_pb.HeartbeatStatus.HEARTBEAT_STATUS_HEALTHY if connected else comm_pb.HeartbeatStatus.HEARTBEAT_STATUS_CONNECTION_ERROR)
        # notification logic
        title = self.fist_name
        content = self.fist_name + " connected"
        if not connected:
            content = self.fist_name + " disconnected"
        notificaton_type = NotificationType.SYSTEM
        self.notify(title, content, notificaton_type)
        self.logger.info('conn_status: ' + str(conn_status))
