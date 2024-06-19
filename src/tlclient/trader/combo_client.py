# auto generated by update_py.py

import queue
import threading
import json
import time
import copy
import functools
from typing import Tuple, Dict, List
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import partial

from tlclient.linker.fist import Fist
from tlclient.linker.timer import Timer
from tlclient.linker.pb_msg import frame_pb
from tlclient.trader.constant import ExchangeID, OffsetFlag, OrderType, Side, OrderStatus
from tlclient.trader.pb_msg import message_pb
from tlclient.trader.client import Client
from tlclient.trader.timer_helper import TimerHelper


def handle_exception(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            func(self, *args, **kwargs)
        except Exception as e:
            info = f'{func.__name__} failed! going to stop myself... (err_info){e}'
            self.logger.exception(info)
            self.stop()
    return wrapper


class ComboOrderState(Enum):
    WAIT_INSERT = 1
    WAIT_ADDITIONAL_INSERT = 2
    DONE = 3
    CANCELED = 4


@dataclass
class ComboResult:
    symbol: str
    traded_vol: float = 0
    traded_price: float = 0
    insert_count: int = 0
    cancel_count: int = 0


@dataclass
class FSMData:
    combo_id: int
    state: ComboOrderState
    index: int = -1
    ratio: float = 1
    order_id: int = 0


@dataclass
class OrderInfo:
    combo_id: int
    index: int
    trading_vol: float
    additional_step: int = 0
    traded_vol: float = 0
    next_remain_vol: float = 0

    _start_time: datetime = field(default_factory=Timer.datetime, init=False)
    _is_cancelled: bool = field(default=False, init=False)


@dataclass
class ComboOrderInfo:
    '''
        combo order下单参数

        Tuple类型的字段之间len必须相等
    '''
    account_id: str  # 账号/tg name
    code: str  # combo分组，后续可以取消属于某组的所有combo order
    tickers: Tuple[str]  # tickers列表，如rb2010, 601816等
    exchanges: Tuple[ExchangeID]  # 交易所列表
    units: Tuple[int]  # 交易量列表
    dirs: Tuple[Side]  # 买卖方向列表
    offsets: Tuple[OffsetFlag]  # 开平方向列表
    start_prices: Tuple[float]  # 下单开始价格列表
    steps: Tuple[float]  # 追单step列表
    stop_prices: Tuple[float]  # 停止下单价格列表
    cancel_intervals: Tuple[float]  # 追单等待时间列表（毫秒）
    time_limit: float  # combo整单限制时长（秒）
    init_delay: float = 0  # 初始delay秒数，即等待init_delay秒后才会开始下单
    sub_account: str = ''  # sub account，不涉及保持默认即可

    _order_infos: Dict[int, OrderInfo] = field(default_factory=dict, init=False)
    _result: Dict[str, ComboResult] = field(default_factory=dict, init=False)
    _start_time: datetime = field(default_factory=Timer.datetime, init=False)
    _done_time: datetime = field(default=None, init=False)
    _combo_order_status: OrderStatus = field(default=OrderStatus.UNKNOWN, init=False)


class ComboClient(Client, TimerHelper):

    def __init__(self, name: str, env_name: str, master_addr: str, curve_server_key=''):
        super().__init__(name=name, env_name=env_name, addr=master_addr, curve_server_key=curve_server_key)
        super(Fist, self).__init__(self.logger)

        # combo id start from this
        self._combo_id_base = 1
        # retrieve combo id by order_id
        self._order_id_to_combo: Dict[int, int] = {}
        # retrieve combo info by combo_id
        self._combo_id_to_combo_info: Dict[int, ComboOrderInfo] = {}
        self._gl = threading.Lock()
        self._fsm_q = queue.Queue()
        # rzw TODO: prefer to set thread's daemon = False
        self._fsm_t = threading.Thread(
            target=self._fsm_func, name='fsm', daemon=True
        )
        self._fsm_t.start()
        self._fsm_timer_t = threading.Thread(
            target=self._fsm_timer_func, name='timer', daemon=True
        )
        self._fsm_timer_t.start()

    def _cancel_order_with_lock(self, combo_id: int, order_id: str, index: int):
        combo_order_info = self._combo_id_to_combo_info[combo_id]
        if self.cancel_order(tg_name=combo_order_info.account_id, order_id=order_id) == -1:
            # rzw TODO
            self.logger.warn(f'[fsm_func] cancel order failed (order_id){order_id} (combo_id){combo_id}')
        else:
            symbol = combo_order_info.ticker
            try:
                combo_order_info._result[symbol].cancel_count += 1
            except KeyError:
                combo_order_info._result[symbol] = ComboResult(symbol=symbol, cancel_count=1)

            self._gl.release()
            self.on_req_order_cancel(order_id)
            self._gl.acquire()

    def _cancel_a_combo_order_with_lock(self, combo_id, order_id_to_skip=None):
        # rzw TODO: prefer to deal with these in fsm
        combo_order_info = self._combo_id_to_combo_info[combo_id]
        if combo_order_info._done_time is not None:
            return
        order_id_cancelled: List[int] = []
        for order_id, order in combo_order_info._order_infos.items():
            # means this order has done, no need to cancel
            if order.traded_vol == combo_order_info.units[order.index]:
                continue
            if (order_id_to_skip is None or order_id != order_id_to_skip):
                if self.cancel_order(tg_name=combo_order_info.account_id, order_id=order_id) == -1:
                    # rzw TODO
                    self.logger.warn(f'[timer_func] cancel order failed when cancelling all unfinished orders of (combo_id){combo_id} (order_id){order_id}')
                else:
                    self.logger.info(f'[timer_func] cancel order {order_id} of combo order {combo_id} (order_info){order} (vol){combo_order_info.units[order.index]}')
                    order_id_cancelled.append(order_id)
                    symbol = combo_order_info.tickers[order.index]
                    try:
                        combo_order_info._result[symbol].cancel_count += 1
                    except KeyError:
                        combo_order_info._result[symbol] = ComboResult(symbol=symbol, cancel_count=1)

        combo_order_info._done_time = Timer.datetime()

        self._gl.release()
        for order_id in order_id_cancelled:
            self.on_req_order_cancel(order_id)
        self._gl.acquire()

    @handle_exception
    def _fsm_func(self):
        self.logger.info(f"{self.fist_name}'s fsm thread started!")
        while not self.is_stopped():
            fsm_data = self._fsm_q.get()
            self.logger.info(f'[fsm_func] got a fsm data {fsm_data}')
            with self._gl:
                try:
                    combo_order_info = self._combo_id_to_combo_info[fsm_data.combo_id]
                except KeyError:
                    self.logger.warn(f'[fsm_func] no this combo id {fsm_data.combo_id} when got the fsm data')
                    self._fsm_q.task_done()
                    continue
                if fsm_data.state == ComboOrderState.WAIT_INSERT:
                    # this branch is for normal inserting(including first contract in a combo, and second one, third one, ..., last one)
                    # the first contract's ratio is 1, ratios of contracts starting from second order are decided by last contract traded ratio
                    exchange = combo_order_info.exchanges[fsm_data.index]
                    volume = combo_order_info.units[fsm_data.index] * fsm_data.ratio
                    symbol = combo_order_info.tickers[fsm_data.index]
                    price = combo_order_info.start_prices[fsm_data.index]
                    side = combo_order_info.dirs[fsm_data.index]
                    offset_flag = combo_order_info.offsets[fsm_data.index]
                    order_id = self.insert_order(tg_name=combo_order_info.account_id,
                                                 exchange=exchange, ticker=symbol, price=price,
                                                 volume=volume, order_type=OrderType.LIMIT, direction=side, offset_flag=offset_flag)
                    self.logger.info(f'[fsm_func] order inserted (order_id){order_id} (combo_id){fsm_data.combo_id} (vol){volume} (price){price} (symbol){symbol}')
                    self._order_id_to_combo[order_id] = fsm_data.combo_id
                    # store every inserted order's info
                    combo_order_info._order_infos[order_id] = OrderInfo(combo_id=fsm_data.combo_id, index=fsm_data.index, trading_vol=volume)
                    try:
                        combo_order_info._result[symbol].insert_count += 1
                    except KeyError:
                        combo_order_info._result[symbol] = ComboResult(symbol=symbol, insert_count=1)
                    self._gl.release()
                    self.on_req_order_insert(order_id, exchange, symbol, price, volume, OrderType.LIMIT, side, offset_flag)
                    self._gl.acquire()
                elif fsm_data.state == ComboOrderState.WAIT_ADDITIONAL_INSERT:
                    order_id = fsm_data.order_id
                    # calculate the new price
                    new_price: float = combo_order_info.start_prices[fsm_data.index] + combo_order_info.steps[fsm_data.index] * (combo_order_info._order_infos[fsm_data.order_id].additional_step + 1) * (1 if combo_order_info.dirs[fsm_data.index] == Side.BUY else -1)

                    order_info = combo_order_info._order_infos[order_id]
                    traded_vol = order_info.traded_vol
                    trading_vol = order_info.trading_vol
                    next_remain_vol = order_info.next_remain_vol
                    additional_step = order_info.additional_step + 1
                    del combo_order_info._order_infos[order_id]

                    exchange = combo_order_info.exchanges[fsm_data.index]
                    side = combo_order_info.dirs[fsm_data.index]
                    offset_flag = combo_order_info.offsets[fsm_data.index]
                    new_order_id = self.insert_order(tg_name=combo_order_info.account_id,
                                                     exchange=exchange, ticker=symbol, price=new_price,
                                                     volume=trading_vol, order_type=OrderType.LIMIT, direction=side, offset_flag=offset_flag)
                    self.logger.info(f'[fsm_func] previous order {order_id} cancelled and additional order {new_order_id} inserted at price {new_price} (combo_id){fsm_data.combo_id} (traded_vol){traded_vol} (vol){trading_vol} (next_remain_vol){next_remain_vol} (step){additional_step}')
                    self._order_id_to_combo[new_order_id] = fsm_data.combo_id
                    # store every inserted order's info
                    combo_order_info._order_infos[new_order_id] = OrderInfo(combo_id=fsm_data.combo_id, index=fsm_data.index, trading_vol=trading_vol, additional_step=additional_step, traded_vol=traded_vol, next_remain_vol=next_remain_vol)
                    try:
                        combo_order_info._result[symbol].insert_count += 1
                    except KeyError:
                        combo_order_info._result[symbol] = ComboResult(symbol=symbol, insert_count=1)

                    self._gl.release()
                    self.on_req_order_insert(new_order_id, exchange, symbol, new_price, trading_vol, OrderType.LIMIT, side, offset_flag)
                    self._gl.acquire()
                elif fsm_data.state == ComboOrderState.DONE:
                    # can not clean datas immediately here, just set a done time and then do the cleaning job in timer thread
                    combo_order_info._done_time = Timer.datetime()
            self._fsm_q.task_done()

    @handle_exception
    def _fsm_timer_func(self):
        self.logger.info(f"{self.fist_name}'s fsm timer thread started!")
        while not self.is_stopped():
            combo_done_list: List[int] = []
            combo_should_cancelled_list: List[int] = []
            with self._gl:
                for combo_id, combo in self._combo_id_to_combo_info.items():
                    now = Timer.datetime()
                    if combo._done_time is not None:
                        if now - combo._done_time >= timedelta(minutes=3):
                            self.logger.info(f'[timer_func] combo order has done, clean all data of it now (combo_id){combo_id}')
                            combo_done_list.append(combo_id)
                    elif now - combo._start_time < timedelta(seconds=combo.time_limit):
                        # self.logger.info(f'[timer_func] order infos {combo._order_infos} (len){len(combo._order_infos)}')
                        for order_id, order in combo._order_infos.items():
                            # self.logger.info(f'[timer_func] order {order_id} info in combo order {combo_id} (traded_vol){order.traded_vol} (unit){combo.units[order.index]}')
                            if order.traded_vol < combo.units[order.index]:
                                # check if some order reached their cancel intervals
                                if not order._is_cancelled and combo.cancel_intervals[order.index] != -1 and now - order._start_time >= timedelta(milliseconds=combo.cancel_intervals[order.index]):
                                    order._is_cancelled = True
                                    reached_stop_price = False
                                    if combo.dirs[order.index] == Side.BUY:
                                        new_price = combo.start_prices[order.index] + (order.additional_step+1) * combo.steps[order.index]
                                        if new_price >= combo.stop_prices[order.index]:
                                            reached_stop_price = True
                                    else:
                                        new_price = combo.start_prices[order.index] + (-1) * (order.additional_step+1) * combo.steps[order.index]
                                        if new_price <= combo.stop_prices[order.index]:
                                            reached_stop_price = True

                                    self.logger.info(f'[timer_func] (new_price){new_price} (stop_price){combo.stop_prices[order.index]} (combo_id){combo_id} (order_id){order_id} (contract){combo.tickers[order.index]}')
                                    if reached_stop_price:
                                        self.logger.warning(f'[timer_func] cancel combo order, due to reached stop price (combo_id){combo_id} (order_id){order_id} (contract){combo.tickers[order.index]}')
                                        combo_should_cancelled_list.append(combo_id)
                                        break
                                    self._cancel_order_with_lock(combo_id, order_id, order.index)
                    else:
                        self.logger.warn(f'[timer_func] combo canceled, since reaching time limit (combo_id){combo_id} (start_time){combo._start_time} (now){now}')
                        combo_should_cancelled_list.append(combo_id)

                if combo_should_cancelled_list:
                    for combo_id in combo_should_cancelled_list:
                        self._cancel_a_combo_order_with_lock(combo_id)
                if combo_done_list:
                    for combo_id in combo_done_list:
                        for order_id in self._combo_id_to_combo_info[combo_id]._order_infos.keys():
                            # delete all order ids belonged to the combo
                            del self._order_id_to_combo[order_id]
                        # delete the combo info
                        del self._combo_id_to_combo_info[combo_id]
                    continue

            time.sleep(0.05)

    def _insert_combo_order(self, order_info: ComboOrderInfo, combo_id: int):
        self._combo_id_to_combo_info[combo_id] = order_info
        self._fsm_q.put(FSMData(combo_id=combo_id, index=0, state=ComboOrderState.WAIT_INSERT))
        self.logger.info(f'[insert_combo_order] (id){combo_id} (info){order_info}')

    def insert_combo_order(self, order_info: ComboOrderInfo):
        init_delay = order_info.init_delay
        with self._gl:
            combo_id = self._combo_id_base
            if init_delay != 0:
                order_info.init_delay = 0
                self.insert_func_after(init_delay, partial(self._insert_combo_order, order_info, combo_id))
            else:
                self._insert_combo_order(order_info, combo_id)
            self._combo_id_base += 1
        return combo_id

    def cancel_all_combo_orders(self, groups=None):
        '''取消所有combo orders, 注意该过程是异步的，需要在 combo_rtn_order_cb 中进行确认'''
        self.logger.info(f'[cancel_all_combo_orders] prepare to cancel all combo orders of groups {groups}')
        with self._gl:
            for combo_id, combo_order in self._combo_id_to_combo_info.items():
                if groups is None or combo_order.code in groups:
                    self._cancel_a_combo_order_with_lock(combo_id)

    def is_combo_order(self, order_id: int) -> bool:
        with self._gl:
            return order_id in self._order_id_to_combo

    def _on_rsp_order_insert(self, obj, frame_nano):
        if not self.is_combo_order(obj.order_id):
            self.on_rsp_order_insert(obj, frame_nano)
            return
        if obj.err_id == frame_pb.ErrType.ERR_TYPE_NO_ERR:
            return

        with self._gl:
            try:
                combo_id = self._order_id_to_combo[obj.order_id]
                combo_order_info = self._combo_id_to_combo_info[combo_id]
                order_info = combo_order_info._order_infos[obj.order_id]
            except KeyError:
                self.logger.warn(f'[on_rsp_order_insert] can not retrieve enough info by order id {obj.order_id}')
                return
            symbol = combo_order_info.tickers[order_info.index]

        self.combo_error_cb(combo_id, symbol, obj.err_msg)

        self.logger.warning(f'[on_rsp_order_insert] to cancel combo order {combo_id} (order_id){obj.order_id} (symbol){symbol}')
        with self._gl:
            # do not call combo_rtn_order_cb here
            self._cancel_a_combo_order_with_lock(combo_id=combo_id, order_id_to_skip=obj.order_id)

    def _on_rsp_order_cancel(self, obj, frame_nano):
        if not self.is_combo_order(obj.order_id):
            self.on_rsp_order_cancel(obj, frame_nano)
            return
        if obj.err_id == frame_pb.ErrType.ERR_TYPE_NO_ERR:
            return

        with self._gl:
            try:
                combo_id = self._order_id_to_combo[obj.order_id]
                combo_order_info = self._combo_id_to_combo_info[combo_id]
                order_info = combo_order_info._order_infos[obj.order_id]
            except KeyError:
                self.logger.warn(f'[on_rsp_order_cancel] can not retrieve enough info by order id {obj.order_id}')
                return
            symbol = combo_order_info.tickers[order_info.index]

        self.combo_error_cb(combo_id, symbol, obj.err_msg)

        self.logger.warning(f'[on_rsp_order_cancel] to cancel combo order {combo_id} (order_id){obj.order_id} (symbol){symbol}')
        with self._gl:
            # do not call combo_rtn_order_cb here
            # self._cancel_a_combo_order_with_lock(combo_id=combo_id, order_id_to_skip=obj.order_id)
            pass

    def _on_rtn_order(self, obj: message_pb.RtnOrder, frame_nano):
        if not self.is_combo_order(obj.order_id):
            self.on_rtn_order(obj, frame_nano)
            return

        if obj.order_status == OrderStatus.UNKNOWN or obj.order_status == OrderStatus.NO_TRADE_QUEUEING:
            return

        with self._gl:
            try:
                combo_id = self._order_id_to_combo[obj.order_id]
                combo_order_info = self._combo_id_to_combo_info[combo_id]
                order_info = combo_order_info._order_infos[obj.order_id]
            except KeyError:
                return

            order_status = obj.order_status
            self.logger.info(f'[on_rtn_order] (order_id){obj.order_id} (combo_id){combo_id} (order_status){order_status}')

            if order_status == OrderStatus.ALL_TRADED:
                if len(combo_order_info._result) == len(combo_order_info.tickers):
                    if order_info.index + 1 < len(combo_order_info.tickers):
                        # if this order is not the last one, should notify part trade instead of all traded
                        order_status = OrderStatus.PART_TRADE_QUEUEING
                    else:
                        # should notify the combo_rtn_order_cb in on_rtn_trade (because it's no traded_price here)
                        combo_order_info._combo_order_status = OrderStatus.ALL_TRADED
                        return

                    result = json.dumps(list(map(lambda x: astuple(x), combo_order_info._result.values())))
                    self._gl.release()
                    self.combo_rtn_order_cb(combo_id=combo_id, result=result, status=order_status)
                    self._gl.acquire()
            elif order_status in (OrderStatus.CANCELED, OrderStatus.NO_TRADE_CANCELED, OrderStatus.PART_TRADE_CANCELED):
                if combo_order_info._done_time is not None:
                    for one in combo_order_info._result.values():
                        if one.traded_vol != 0:
                            order_status = OrderStatus.PART_TRADE_CANCELED
                            break
                    else:
                        order_status = OrderStatus.CANCELED
                    if len(combo_order_info._result) < len(combo_order_info.tickers):
                        for symbol in combo_order_info.tickers:
                            if symbol not in combo_order_info._result:
                                combo_order_info._result[symbol] = ComboResult(symbol=symbol)
                    result = json.dumps(list(map(lambda x: astuple(x), combo_order_info._result.values())))
                    self.combo_rtn_order_cb(combo_id=combo_id, result=result, status=order_status)
                else:
                    self._fsm_q.put(FSMData(combo_id=combo_id, index=order_info.index, order_id=obj.order_id, state=ComboOrderState.WAIT_ADDITIONAL_INSERT))

    def _on_rtn_trade(self, obj: message_pb.RtnTrade, frame_nano):
        if not self.is_combo_order(obj.order_id):
            self.on_rtn_trade(obj, frame_nano)
            return

        with self._gl:
            try:
                combo_id = self._order_id_to_combo[obj.order_id]
                combo_order_info = self._combo_id_to_combo_info[combo_id]
                order_info = combo_order_info._order_infos[obj.order_id]
            except KeyError:
                return

            self.logger.info(f'[on_rtn_trade] (order_id){obj.order_id} (combo_id){combo_id} (traded_price){obj.traded_price} (traded_vol){obj.traded_vol} (vol){combo_order_info.units[order_info.index]}')
            result = combo_order_info._result[obj.symbol]
            total_traded = result.traded_vol + obj.traded_vol
            if total_traded != 0:
                result.traded_price = (result.traded_vol * result.traded_price + obj.traded_vol * obj.traded_price) / total_traded
                result.traded_vol = total_traded

            order_info.traded_vol += obj.traded_vol
            order_info.next_remain_vol += obj.traded_vol
            order_info.trading_vol -= obj.traded_vol
            if order_info.index + 1 < len(combo_order_info.tickers):
                # if this order is not the last one, start to insert next order with ratio
                ratio = order_info.next_remain_vol / combo_order_info.units[order_info.index]
                if ratio >= 1:
                    order_info.next_remain_vol = 0
                    self._fsm_q.put(FSMData(combo_id=combo_id, index=order_info.index+1, state=ComboOrderState.WAIT_INSERT, ratio=ratio))
                else:
                    self.logger.info(f'[on_rtn_trade] would not insert order for next contract, since (ratio){ratio} is less than 1, wait more rtn trade (remain_traded_vol){order_info.next_remain_vol}')
            elif combo_order_info._combo_order_status == OrderStatus.ALL_TRADED:
                cb_result = json.dumps(list(map(lambda x: astuple(x), combo_order_info._result.values())))
                self._gl.release()
                self.combo_rtn_order_cb(combo_id=combo_id, result=cb_result, status=OrderStatus.ALL_TRADED)
                self._gl.acquire()
                # if it's the last one and order status marked ALL_TRADED, put a done event into fsm
                self._fsm_q.put(FSMData(combo_id=combo_id, state=ComboOrderState.DONE))

    # should be overrided
    def combo_rtn_order_cb(self, combo_id, result, status):
        pass

    def combo_error_cb(self, combo_id, contract, err_msg):
        pass

    # could override these two callback func
    def on_req_order_insert(self, order_id: int, exchange: ExchangeID, symbol: str, price: float, vol: float, order_type: OrderType, side: Side, offset_flag: OffsetFlag):
        pass

    def on_req_order_cancel(self, order_id: int):
        pass
