# auto generated by update_py.py

import ctypes

from tlclient.linker.timer import Timer
from tlclient.linker.utility import bytify
from tlclient.trader.constant import (AssetType, BarType, ExchangeID, MODULE_TICKER_LENGTH,
                             MODULE_TRADINGDAY_LENGTH, MsgType, ORDER_BOOK_SIZE)


class MktInfo(object):

    def __init__(self, d=None):
        d = d or dict()
        self.exchange = ExchangeID.parse(d.get('exchange'))
        self.ticker = d.get('ticker')
        self.msg_type = d.get('msg_type')
        self.bar_type = BarType.parse(d.get('bar_type'))

    def __str__(self):
        return '<subscribe> exchange={} ticker={} msg_type={} bar_type={}'.format(
            ExchangeID.read(self.exchange), self.ticker,
            MsgType.read(self.msg_type), BarType.read(self.bar_type)
        )

    def to_dict(self):
        return {
            'exchange': self.exchange,
            'ticker': self.ticker,
            'msg_type': self.msg_type,
            'bar_type': self.bar_type
        }


class MktBasic(ctypes.Structure):
    _fields_ = [
        ('exchange', ctypes.c_short),
        ('ticker', ctypes.c_char * MODULE_TICKER_LENGTH),
        ('asset_type', ctypes.c_short),
        ('mkt_time', ctypes.c_int64),
        ('trading_day', ctypes.c_char * MODULE_TRADINGDAY_LENGTH)
    ]

    def __str__(self):
        return '{}-{}-{}-{}-{}'.format(
            ExchangeID.read(self.exchange), self.ticker.decode(), AssetType.read(self.asset_type),
            self.trading_day.decode(), Timer.nano_to_datetime(self.mkt_time).strftime('%H:%M:%S')
        )

    def to_dict(self):
        return {
            'exchange': self.exchange,
            'ticker': self.ticker.decode(),
            'asset_type': self.asset_type,
            'mkt_time': self.mkt_time,
            'trading_day': self.trading_day.decode(),
        }

    def to_influx(self):
        return {
            "measurement": None,
            "tags": {
                "exchange": ExchangeID.read(self.exchange),
                "ticker": self.ticker.decode(),
                "asset_type": AssetType.read(self.asset_type),
                "trading_day": self.trading_day.decode(),
            },
            "time": Timer.nano_to_datetime(self.mkt_time),
            "fields": {
            }
        }


class MktSnap(MktBasic):
    _fields_ = [
        ('ask_price', ctypes.c_double * ORDER_BOOK_SIZE),
        ('bid_price', ctypes.c_double * ORDER_BOOK_SIZE),
        ('ask_volume', ctypes.c_double * ORDER_BOOK_SIZE),
        ('bid_volume', ctypes.c_double * ORDER_BOOK_SIZE)
    ]

    def __str__(self):
        return '<snap-{} ask1={}@{} bid1={}@{}>'.format(
            MktBasic.__str__(self),
            self.ask_volume[0], self.ask_price[0],
            self.bid_volume[0], self.bid_price[0],
        )

    def to_dict(self):
        return dict(MktBasic.to_dict(self), **{
            'ask_prices': list(self.ask_price),
            'bid_prices': list(self.bid_price),
            'ask_volumes': list(self.ask_volume),
            'bid_volumes': list(self.bid_volume),
        })

    def to_influx(self):
        return {
            "measurement": "MktSnapOpt",
            "tags": MktBasic.to_influx(self)['tags'],
            "time": Timer.nano_to_datetime(self.mkt_time),
            "fields": dict(MktBasic.to_influx(self)['fields'], **{
                "ask_price1": self.ask_price[0],
                "ask_price2": self.ask_price[1],
                "ask_price3": self.ask_price[2],
                "ask_price4": self.ask_price[3],
                "ask_price5": self.ask_price[4],
                "ask_volume1": self.ask_volume[0],
                "ask_volume2": self.ask_volume[1],
                "ask_volume3": self.ask_volume[2],
                "ask_volume4": self.ask_volume[3],
                "ask_volume5": self.ask_volume[4],
                "bid_price1": self.bid_price[0],
                "bid_price2": self.bid_price[1],
                "bid_price3": self.bid_price[2],
                "bid_price4": self.bid_price[3],
                "bid_price5": self.bid_price[4],
                "bid_volume1": self.bid_volume[0],
                "bid_volume2": self.bid_volume[1],
                "bid_volume3": self.bid_volume[2],
                "bid_volume4": self.bid_volume[3],
                "bid_volume5": self.bid_volume[4],
            })
        }

    def to_kdb(self):
        dt = Timer.nano_to_datetime(self.mkt_time)
        return [
            dt.date(), dt.time(), self.ticker.decode("utf-8"),
            ExchangeID.read(self.exchange), AssetType.read(self.asset_type),
            list(self.ask_price), list(self.ask_volume),
            list(self.bid_price), list(self.bid_volume)
        ]


class MktSnapPlus(MktSnap):
    _fields_ = [
        ('upper_limit_price', ctypes.c_double),
        ('lower_limit_price', ctypes.c_double),
        ('last_price', ctypes.c_double),
        ('pre_close_price', ctypes.c_double),
        ('open_price', ctypes.c_double),
        ('high_price', ctypes.c_double),
        ('low_price', ctypes.c_double),
        ('close_price', ctypes.c_double),
        ('volume', ctypes.c_double),
        ('turnover', ctypes.c_double),
        ('trading_count', ctypes.c_int64),
    ]

    def __str__(self):
        return '<snap-{} last_px={} vol={} ask1={}@{} bid1={}@{}>'.format(
            MktBasic.__str__(self),
            self.last_price, self.volume,
            self.ask_volume[0], self.ask_price[0],
            self.bid_volume[0], self.bid_price[0],
        )

    def to_dict(self):
        return dict(MktSnap.to_dict(self), **{
            'upper_limit_price': self.upper_limit_price,
            'lower_limit_price': self.lower_limit_price,
            'last_price': self.last_price,
            'pre_close_price': self.pre_close_price,
            'open_price': self.open_price,
            'high_price': self.high_price,
            'low_price': self.low_price,
            'close_price': self.close_price,
            'volume': self.volume,
            'turnover': self.turnover,
            'trading_count': self.trading_count,
        })

    def to_influx(self):
        return {
            "measurement": "MktSnapOpt",
            "tags": MktSnap.to_influx(self)['tags'],
            "time": Timer.nano_to_datetime(self.mkt_time),
            "fields": dict(MktSnap.to_influx(self)['fields'], **{
                "upper_limit_price": self.upper_limit_price,
                "lower_limit_price": self.lower_limit_price,
                "last_price": self.last_price,
                "pre_close_price": self.pre_close_price,
                "open_price": self.open_price,
                "high_price": self.high_price,
                "low_price": self.low_price,
                "close_price": self.close_price,
                "volume": self.volume,
                "turnover": self.turnover,
                "trading_count": self.trading_count,
            })
        }


class MktSnapFut(MktSnapPlus):
    _fields_ = [
        ('pre_open_interest', ctypes.c_double),
        ('open_interest', ctypes.c_double),
        ('pre_settlement_price', ctypes.c_double),
        ('settlement_price', ctypes.c_double)
    ]

    def to_dict(self):
        return dict(MktSnapPlus.to_dict(self), **{
            'pre_open_interest': self.pre_open_interest,
            'open_interest': self.open_interest,
            'pre_settlement_price': self.pre_settlement_price,
            'settlement_price': self.settlement_price
        })

    def to_influx(self):
        return {
            "measurement": "MktSnapOpt",
            "tags": MktSnapPlus.to_influx(self)['tags'],
            "time": Timer.nano_to_datetime(self.mkt_time),
            "fields": dict(MktSnapPlus.to_influx(self)['fields'], **{
                "pre_open_interest": self.pre_open_interest,
                "open_interest": self.open_interest,
                "pre_settlement_price": self.pre_settlement_price,
                "settlement_price": self.settlement_price,
            })
        }


class MktSnapOpt(MktSnapFut):
    _fields_ = [
        ('pre_delta', ctypes.c_double),
        ('curr_delta', ctypes.c_double),
    ]

    def to_dict(self):
        return dict(MktSnapFut.to_dict(self), **{
            'pre_delta': self.pre_delta,
            'curr_delta': self.curr_delta
        })

    def to_influx(self):
        return {
            "measurement": "MktSnapOpt",
            "tags": MktSnapFut.to_influx(self)['tags'],
            "time": Timer.nano_to_datetime(self.mkt_time),
            "fields": dict(MktSnapFut.to_influx(self)['fields'], **{
                "pre_delta": self.pre_delta,
                "curr_delta": self.curr_delta
            })
        }


class MktVolumeDetail:

    # init from a list (parsed from json)
    def __init__(self, d=None):
        self.exchange = None if d is None else ExchangeID.parse(d[0])
        self.volume = None if d is None else float(d[1])

    def __str__(self):
        return '<vd ex={} v={}>'.format(ExchangeID.read(self.exchange), self.volume)


class MktPriceLevel:

    # init from a list (parsed from json)
    def __init__(self, d=None):
        self.price = None if d is None else float(d[0])
        self.volume = None if d is None else float(d[1])
        self.details = [] if d is None else [MktVolumeDetail(dd) for dd in d[2]]

    def __str__(self):
        return '<pl p={} v={} detail={}>'.format(self.price, self.volume, '/'.join(map(lambda x: str(x), self.details)))


class MktSnapAgg(MktSnap):

    # init from a dist (parsed from json)
    def __init__(self, d):
        d = d or {}
        self.exchange = ExchangeID.parse(d.get('exchange',  ExchangeID.read(ExchangeID.NOT_AVAILABLE)))
        self.ticker = bytify(d.get('ticker', ''))
        self.asset_type = AssetType.parse(d.get('asset_type', AssetType.read(AssetType.NOT_AVAILABLE)))
        self.mkt_time = d.get('mkt_time', -1)
        self.trading_day = bytify(d.get('trading_day', ''))
        ask_prices = d.get('ask_prices')
        bid_prices = d.get('bid_prices')
        ask_volumes = d.get('ask_volumes')
        bid_volumes = d.get('bid_volumes')
        for i in range(0, ORDER_BOOK_SIZE):
            self.ask_price[i] = ask_prices[i] if ask_prices else 0
            self.bid_price[i] = bid_prices[i] if bid_prices else 0
            self.ask_volume[i] = ask_volumes[i] if ask_volumes else 0
            self.bid_volume[i] = bid_volumes[i] if bid_volumes else 0
        self.bid_levels = [MktPriceLevel(dd) for dd in d.get('bid_levels', [])]
        self.ask_levels = [MktPriceLevel(dd) for dd in d.get('ask_levels', [])]

    def __str__(self):
        return '<snap-{} ask1={}@{} bid1={}@{} al1={} bl1={}>'.format(
            MktBasic.__str__(self),
            self.ask_volume[0], self.ask_price[0],
            self.bid_volume[0], self.bid_price[0],
            None if len(self.ask_levels) == 0 else str(self.ask_levels[0]),
            None if len(self.bid_levels) == 0 else str(self.bid_levels[0]),
        )


class MktIndex(MktBasic):
    _fields_ = [
        ('last', ctypes.c_double),
        ('pre_close', ctypes.c_double),
        ('open', ctypes.c_double),
        ('high', ctypes.c_double),
        ('low', ctypes.c_double),
        ('close', ctypes.c_double),
        ('volume', ctypes.c_double),
        ('turnover', ctypes.c_double),
    ]

    def to_dict(self):
        return dict(MktBasic.to_dict(self), **{
            'last': self.last,
            'pre_close': self.pre_close,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume,
            'turnover': self.turnover
        })

    def to_influx(self):
        return {
            "measurement": "MktIndex",
            "tags": MktBasic.to_influx(self)['tags'],
            "time": Timer.nano_to_datetime(self.mkt_time),
            "fields": dict(MktBasic.to_influx(self)['fields'], **{
                'last': self.last,
                'pre_close': self.pre_close,
                'open': self.open,
                'high': self.high,
                'low': self.low,
                'close': self.close,
                'volume': self.volume,
                'turnover': self.turnover
            })
        }

    def __str__(self):
        return '<Index-{} last={} vol={} ohlc={}|{}|{}|{}>'.format(
            MktBasic.__str__(self), self.last, self.volume, self.open, self.high, self.low, self.close,
        )


class MktOrder(MktBasic):
    _fields_ = [
        ('group_id', ctypes.c_int64),
        ('index', ctypes.c_int64),
        ('price', ctypes.c_double),
        ('volume', ctypes.c_double),
        ('order_type', ctypes.c_short),
    ]

    def __str__(self):
        return '<md_order-{} group_id={} index={} price={} volume={} order_type={}>'.format(
            MktBasic.__str__(self),
            self.group_id, self.index,
            self.price, self.volume,
            self.order_type
        )

    def to_dict(self):
        return dict(MktBasic.to_dict(self), **{
            'group_id': self.group_id,
            'index': self.index,
            'price': self.price,
            'volume': self.volume,
            'order_type': self.order_type
        })

    def to_influx(self):
        return {
            "measurement": "MktOrder",
            "tags": dict(MktBasic.to_influx(self)['tags'], **{
                'group_id': self.group_id,
                'order_type': self.order_type,
                'index': self.index
            }),
            "time": Timer.nano_to_datetime(self.mkt_time),
            "fields": dict(MktBasic.to_influx(self)['fields'], **{
                'price': self.price,
                'volume': self.volume
            })
        }


class MktTrade(MktBasic):
    _fields_ = [
        ('group_id', ctypes.c_int64),
        ('index', ctypes.c_int64),
        ('price', ctypes.c_double),
        ('volume', ctypes.c_double),
        ('order_type', ctypes.c_short),
        ('buy_order_index', ctypes.c_int64),
        ('sell_order_index', ctypes.c_int64),
    ]

    def __str__(self):
        return '<md_trade-{} group_id={} index={} price={} volume={} order_type={} buy_order={} sell_order={}>'.format(
            MktBasic.__str__(self),
            self.group_id, self.index,
            self.price, self.volume,
            self.order_type,
            self.buy_order_index, self.sell_order_index
        )

    def to_dict(self):
        return dict(MktBasic.to_dict(self), **{
            'group_id': self.group_id,
            'index': self.index,
            'price': self.price,
            'volume': self.volume,
            'order_type': self.order_type,
            'buy_order_index': self.buy_order_index,
            'sell_order_index': self.sell_order_index
        })

    def to_influx(self):
        return {
            "measurement": "MktTrade",
            "tags": dict(MktBasic.to_influx(self)['tags'], **{
                'group_id': self.group_id,
                'index': self.index,
                'order_type': self.order_type,
                'buy_order_index': self.buy_order_index,
                'sell_order_index': self.sell_order_index
            }),
            "time": Timer.nano_to_datetime(self.mkt_time),
            "fields": dict(MktBasic.to_influx(self)['fields'], **{
                'price': self.price,
                'volume': self.volume
            })
        }

    def to_kdb(self):
        dt = Timer.nano_to_datetime(self.mkt_time)
        order_type = "null"  # todo, refactor order type here
        return [
            dt.date(), dt.time(), self.ticker.decode('utf-8'), ExchangeID.read(self.exchange),
            AssetType.read(self.asset_type), self.group_id, self.index, self.price,
            self.volume, order_type, self.buy_order_index, self.sell_order_index
        ]


class MktBar(MktBasic):
    _fields_ = [
        ('sec_interval', ctypes.c_int),
        ('open', ctypes.c_double),
        ('close', ctypes.c_double),
        ('low', ctypes.c_double),
        ('high', ctypes.c_double),
        ('volume', ctypes.c_double),
    ]

    def __str__(self):
        return '<bar/{}-{} O={} C={} L={} H={} V={}>'.format(
            self.sec_interval, MktBasic.__str__(self),
            self.open, self.close, self.low, self.high, self.volume,
        )

    def to_dict(self):
        return dict(MktBasic.to_dict(self), **{
            'sec_interval': self.sec_interval,
            'open': self.open,
            'close': self.close,
            'low': self.low,
            'high': self.high,
            'volume': self.volume
        })

    def to_influx(self):
        return {
            "measurement": "MktBarGen",
            "tags": dict(MktBasic.to_influx(self)['tags'], **{
                'sec_interval': self.sec_interval
            }),
            "time": Timer.nano_to_datetime(self.mkt_time),
            "fields": dict(MktBasic.to_influx(self)['fields'], **{
                'open': self.open,
                'close': self.close,
                'low': self.low,
                'high': self.high,
                'volume': self.volume
            })
        }

    def to_kdb(self):
        dt = Timer.nano_to_datetime(self.mkt_time)
        return [
            dt.date(), dt.time(), self.ticker.decode("utf-8"), ExchangeID.read(self.exchange),
            AssetType.read(self.asset_type), self.sec_interval,
            self.open, self.close, self.high, self.low, self.volume
        ]


class MktBarGen(MktBar):
    _fields_ = [
        ('start_nano', ctypes.c_int64),
        ('end_nano', ctypes.c_int64),
        ('start_volume', ctypes.c_double),
    ]

    def to_dict(self):
        return dict(MktBar.to_dict(self), **{
            'start_nano': self.start_nano,
            'end_nano': self.end_nano,
            'start_volume': self.start_volume
        })

    def to_influx(self):
        return {
            "measurement": "MktBarGen",
            "tags": dict(MktBar.to_influx(self)['tags'], **{
                'start_nano': self.start_nano,
                'end_nano': self.end_nano,
                'start_volume': self.start_volume,
            }),
            "time": Timer.nano_to_datetime(self.mkt_time),
            "fields": MktBar.to_influx(self)['fields']
        }


class MktVol(MktBar):
    _fields_ = [
        ('sample_num', ctypes.c_int64),
        ('sample_std', ctypes.c_double),
    ]

    def to_dict(self):
        return dict(MktBar.to_dict(self), **{
            'sample_num': self.sample_num,
            'sample_std': self.sample_std
        })

    def to_influx(self):
        return {
            "measurement": "MktVol",
            "tags": MktBar.to_influx(self)['tags'],
            "time": Timer.nano_to_datetime(self.mkt_time),
            "fields": dict(MktBar.to_influx(self)['fields'], **{
                'sample_num': self.sample_num,
                'sample_std': self.sample_std
            }),
        }
