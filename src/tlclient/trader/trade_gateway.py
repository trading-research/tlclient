# auto generated by update_py.py

from collections import defaultdict

from tlclient.linker.constant import FistType
from tlclient.trader.gateway import Gateway
from tlclient.trader.pb_msg import message_pb, MsgType


class TradeGateway(Gateway):

    def __init__(self, acc_name, gateway_name, env_name, addr):
        Gateway.__init__(self, acc_name, gateway_name, env_name, addr, FistType.TRADE_GATEWAY)
        self._req_positions = defaultdict(list)

    def init_oms(self, oms_name):
        init_orders = message_pb.GatewayOrders()
        init_orders.account_id = self.fist_name
        try:
            self.reg_req(oms_name)

            req = message_pb.ReqActiveOrders()
            req.account_id = self.fist_name
            req.sender = self.fist_name
            ret = self.req(oms_name, req, MsgType.MSG_TYPE_REQ_ACTIVE_ORDERS, 0)
            err_id = ret.get_err_id()
            if err_id == 0:
                init_orders = ret.get_obj(message_pb.GatewayOrders)
            else:
                init_orders.err_id = err_id
                init_orders.err_msg = 'get init orders error'

        except Exception as e:
            init_orders.err_id = message_pb.ErrType.ERR_TYPE_OMS_NOT_FOUND
            init_orders.err_msg = str(e)

        self.on_rsp_init_orders(init_orders)

    # --------- overrides ---------
    #
    def on_req_plain_order_insert(self, obj, frame_nano):
        pass
    
    def on_req_algo_order_insert(self, obj, frame_nano):
        pass

    def on_req_order_cancel(self, obj, frame_nano):
        pass

    def on_req_position(self, obj, req_id, frame_nano):
        pass

    def on_req_account(self, obj, req_id, frame_nano):
        pass

    def on_req_active_orders(self, obj, req_id, frame_nano):
        pass

    def on_req_cancel_active_orders(self, obj, req_id, frame_nano):
        pass

    def on_req_history_trades(self, obj, req_id, frame_nano):
        pass

    def on_rsp_init_orders(self, obj):
        pass

    # --------- internals ---------
    #
    def _on_req_plain_order_insert(self, obj, frame_nano):
        if obj.account_id == self.fist_name:
            self.on_req_plain_order_insert(obj, frame_nano)
            
    def _on_req_algo_order_insert(self, obj, frame_nano):
        if obj.account_id == self.fist_name:
            self.on_req_algo_order_insert(obj, frame_nano)

    def _on_req_order_cancel(self, obj, frame_nano):
        if obj.account_id == self.fist_name:
            self.on_req_order_cancel(obj, frame_nano)

    def _on_req_position(self, obj, req_id, frame_nano):
        if obj.account_id == self.fist_name:
            self.on_req_position(obj, req_id, frame_nano)

    def _on_req_account(self, obj, req_id, frame_nano):
        if obj.account_id == self.fist_name:
            self.on_req_account(obj, req_id, frame_nano)

    def _on_req_active_orders(self, obj, req_id, frame_nano):
        if obj.account_id == self.fist_name:
            self.on_req_active_orders(obj, req_id, frame_nano)

    def _on_req_cancel_active_orders(self, obj, req_id, frame_nano):
        if obj.account_id == self.fist_name:
            self.on_req_cancel_active_orders(obj, req_id, frame_nano)

    def _on_req_history_trades(self, obj, req_id, frame_nano):
        if obj.account_id == self.fist_name:
            self.on_req_history_trades(obj, req_id, frame_nano)

    def on_pub_frame(self, f):
        msg_type = f.get_msg_type()
        frame_nano = f.get_nano()
        if msg_type == MsgType.MSG_TYPE_REQ_ORDER_INSERT:
            obj = f.get_obj(message_pb.ReqOrderInsert)
            self._on_req_plain_order_insert(obj, frame_nano)
        elif msg_type == MsgType.MSG_TYPE_REQ_ORDER_INSERT_J:
            obj = f.get_obj(message_pb.ReqOrderInsert)
            self._on_req_algo_order_insert(obj, frame_nano)
        elif msg_type == MsgType.MSG_TYPE_REQ_ORDER_CANCEL:
            obj = f.get_obj(message_pb.ReqOrderCancel)
            self._on_req_order_cancel(obj, frame_nano)
        elif msg_type == MsgType.MSG_TYPE_REQ_POSITION:
            obj = f.get_obj(message_pb.ReqPosition)
            self._on_req_position(obj, f.get_req_id(), frame_nano)
        elif msg_type == MsgType.MSG_TYPE_REQ_ACCOUNT:
            obj = f.get_obj(message_pb.ReqAccount)
            self._on_req_account(obj, f.get_req_id(), frame_nano)
        elif msg_type == MsgType.MSG_TYPE_REQ_ACTIVE_ORDERS:
            obj = f.get_obj(message_pb.ReqActiveOrders)
            self._on_req_active_orders(obj, f.get_req_id(), frame_nano)
        elif msg_type == MsgType.MSG_TYPE_REQ_CANCEL_ACTIVE_ORDERS:
            obj = f.get_obj(message_pb.ReqCancelActiveOrders)
            self._on_req_cancel_active_orders(obj, f.get_req_id(), frame_nano)
        elif msg_type == MsgType.MSG_TYPE_REQ_HISTORY_TRADES:
            obj = f.get_obj(message_pb.ReqHistoryTrades)
            self._on_req_history_trades(obj, f.get_req_id(), frame_nano)

    # --------- utilities for gateway ---------
    #
    def push_rsp_order_insert(self, order_id, order_ref='', err_id=0, err_msg=''):
        obj = message_pb.RspOrderInsert()
        obj.order_id = order_id
        obj.order_ref = order_ref
        obj.err_id = err_id
        obj.err_msg = err_msg

        self.safe_push(obj, MsgType.MSG_TYPE_RSP_ORDER_INSERT, obj.order_id)
    
    def push_rsp_order_cancel(self, req_id, order_id, order_ref='', err_id=0, err_msg=''):
        obj = message_pb.RspOrderCancel()
        obj.req_id = req_id
        obj.order_id = order_id
        obj.order_ref = order_ref
        obj.err_id = err_id
        obj.err_msg = err_msg

        self.safe_push(obj, MsgType.MSG_TYPE_RSP_ORDER_CANCEL, obj.req_id)

    def push_rtn_order(self, obj):
        self.safe_push(obj, MsgType.MSG_TYPE_RTN_ORDER, obj.order_id)

    def push_rtn_trade(self, obj):
        self.safe_push(obj, MsgType.MSG_TYPE_RTN_TRADE, obj.order_id)

    def push_position(self, obj, req_id):
        obj.pos_id = req_id
        self.safe_push(obj, MsgType.MSG_TYPE_RSP_POSITION, req_id)

    def push_pos_info(self, obj, req_id, is_last):
        if obj is not None:
            self._req_positions[req_id].append(obj)

        if is_last:
            rsp_pos = message_pb.GatewayPosition()
            rsp_pos.account_id = self.gateway_name
            rsp_pos.positions.extend(self._req_positions[req_id])

            self.push_position(rsp_pos, req_id)
            self._req_positions.pop(req_id)

    def push_account(self, obj, req_id):
        obj.req_id = req_id
        self.safe_push(obj, MsgType.MSG_TYPE_RSP_ACCOUNT, req_id)

    def push_active_orders(self, obj, req_id):
        obj.req_id = req_id
        self.safe_push(obj, MsgType.MSG_TYPE_RSP_ACTIVE_ORDERS, req_id)

    def push_cancel_active_ordres(self, req_id, err_id=0, err_msg=''):
        obj = message_pb.RspCancelActiveOrders()
        obj.err_id = err_id
        obj.err_msg = err_msg

        self.safe_push(obj, MsgType.MSG_TYPE_RSP_CANCEL_ACTIVE_ORDERS, req_id)

    def push_history_trades(self, obj, req_id):
        obj.req_id = req_id
        self.safe_push(obj, MsgType.MSG_TYPE_RSP_HISTORY_TRADES, req_id)
