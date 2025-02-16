# auto generated by update_py.py
import requests
import pandas
import time
import datetime

from tlclient.trader.data_manager.dm_error import DMError

class DMClient:
    API_HOST = "http://tl-api-prod-2137008819.cn-northwest-1.elb.amazonaws.com.cn/"
    API_VERSION = "v1"

    @classmethod
    def __date2str(self, date):
        return date.strftime('%Y-%m-%d')

    @classmethod
    def __compact_to_map(self, keys, vals):
        res = {}
        for i in range(len(keys)):
            key = keys[i]
            val = vals[i]
            if val is not None:
                res[key] = val
        return res

    def __init__(self, api_key, secret_key):
        self.api_key = api_key
        self.secret_key = secret_key
        self.access_token = None
        self.expired_in = 0

    def __request_base(self, url):
        res = requests.get(url)
        json = res.json()
        if res.status_code == 200:
            return json
        else:
            raise DMError(json['error'], json['detail'])

    def __check_expired(self):
        current_time = time.time()
        return self.expired_in < current_time

    def __refresh_token_if_needed(self):
        # use current access_token if not expired
        if self.access_token is not None and not self.__check_expired():
            return

        endpoint = "auth/access_token"
        url = "{}/{}?api_key={}&secret_key={}".format(self.API_HOST, endpoint, self.api_key, self.secret_key)
        res = self.__request_base(url)
        self.access_token = res['token']
        self.expired_in = res['expired_in']

    def __request(self, endpoint, arguments):
        args = "&".join("{}={}".format(k, v) for k, v in arguments.items())
        args += "&token={}".format(self.access_token)
        url = "{}/{}/{}?{}".format(self.API_HOST, self.API_VERSION, endpoint, args)
        return self.__request_base(url)

    def get_instruments(self, exchange=None, type=None, date=None):
        self.__refresh_token_if_needed()
        if date is not None:
            date = DMClient.__date2str(date)
        args = DMClient.__compact_to_map(
                ['exchange', 'intrument_type', 'date'],
                [exchange, type, date]
                )
        res = self.__request('instruments', args)
        return pandas.DataFrame(res['instruments'])

    def get_instrument_info(self, symbols=None):
        self.__refresh_token_if_needed()
        args = {}
        if isinstance(symbols, str):
            args = DMClient.__compact_to_map(['symbols_reg'], [symbols])
        elif isinstance(symbols, list):
            args = DMClient.__compact_to_map(['symbols_arr'], [','.join(symbols)])
        res = self.__request('instrument_infos', args)
        return pandas.DataFrame(res['instrument_infos'])

    def get_days_listed(self, symbols, non_trans_include=True, date=None):
        self.__refresh_token_if_needed()
        if date is not None:
            date = DMClient.__date2str(date)
        args = {}
        if isinstance(symbols, str):
            args = DMClient.__compact_to_map(
                    ['symbols_reg', 'non_trans_include', 'date'],
                    [symbols, non_trans_include, date])
        elif isinstance(symbols, list):
            args = DMClient.__compact_to_map(
                    ['symbols_arr', 'non_trans_include', 'date'],
                    [','.join(symbols), non_trans_include, date])
        res = self.__request('days_listed', args)
        return pandas.DataFrame([{'symbol': k, 'day': v} for k, v in res.items()])

    def get_days_to_expire(self, symbols, non_trans_include=True, date=None):
        self.__refresh_token_if_needed()
        if date is not None:
            date = DMClient.__date2str(date)
        args = {}
        if isinstance(symbols, str):
            args = DMClient.__compact_to_map(
                    ['symbols_reg', 'non_trans_include', 'date'],
                    [symbols, non_trans_include, date])
        elif isinstance(symbols, list):
            args = DMClient.__compact_to_map(
                    ['symbols_arr', 'non_trans_include', 'date'],
                    [','.join(symbols), non_trans_include, date])
        res = self.__request('days_to_expire', args)
        return pandas.DataFrame([{'symbol': k, 'day': v} for k, v in res.items()])

    def get_trading_dates(self, exchange, start_date, end_date):
        self.__refresh_token_if_needed()
        args = DMClient.__compact_to_map(
                ['exchange', 'start_date', 'end_date'],
                [exchange, DMClient.__date2str(start_date), DMClient.__date2str(end_date)])
        res = self.__request('trading_dates', args)
        return pandas.Series([datetime.datetime.strptime(d, '%Y-%m-%d') for d in res])

    def get_trading_dates_count(self, exchange, count, date):
        another_date = date - datetime.timedelta(days=count*2)
        start_date = min([date, another_date])
        end_date = max([date, another_date])
        res = self.get_trading_dates(exchange, start_date, end_date)
        return res[0:abs(count)]

    def get_history_data(self, symbol, start_date, end_date, frequency='1m', fields=[], adjust_type=None, fill_flag=False):
        self.__refresh_token_if_needed()
        args = DMClient.__compact_to_map(
                ['symbol', 'start_date', 'end_date', 'frequency', 'fields', 'adjust_type'],
                [symbol, DMClient.__date2str(start_date), DMClient.__date2str(end_date), frequency, ",".join(fields), adjust_type])
        res = self.__request('history_bar', args)
        if not fill_flag:
            return pandas.DataFrame(res)

        current_nano = res[0]['time']
        res = dict([(r['time'], r) for r in res])
        end_nano = int(end_date.strftime('%s')) * 1000000000
        one_minute_nano = 60000000000
        if fill_flag:
            interval = one_minute_nano
            if frequency == '1m':
                interval = one_minute_nano
            elif frequency == '5m':
                interval = one_minute_nano * 5
            elif frequency == '1h':
                interval = one_minute_nano * 60
            elif frequency == '1d':
                interval = one_minute_nano * 60 * 24

        filled_res = []
        while current_nano <= end_nano:
            if current_nano in res:
                filled_res.append(res[current_nano])
            else:
                ele = {}
                if len(filled_res) != 0:
                    ele = filled_res[len(filled_res) - 1]
                ele['time'] = current_nano
                filled_res.append(ele)
            current_nano += interval
        return pandas.DataFrame(filled_res)

    def get_history_tick_data(self, symbol, date):
        self.__refresh_token_if_needed()
        args = DMClient.__compact_to_map(
                ['symbol', 'date'],
                [symbol, DMClient.__date2str(date)])
        res = self.__request('history_tick', args)
        return pandas.DataFrame(res['snapshots'])

    def get_adjust_factor(self, symbols, start_date, end_date):
        self.__refresh_token_if_needed()
        args = DMClient.__compact_to_map(
                ['start_date', 'end_date'],
                [DMClient.__date2str(start_date), DMClient.__date2str(end_date)])
        if isinstance(symbols, str):
            args.update({'symbols_reg', symbols})
        elif isinstance(symbols, list):
            args.update({'symbols_arr': ','.join(symbols)})
        res = self.__request('adjust_factor', args)
        return pandas.DataFrame(res)

    def is_suspended(self, symbols, start_date, end_date):
        self.__refresh_token_if_needed()
        args = DMClient.__compact_to_map(
                ['symbols_arr', 'start_date', 'end_date'],
                [','.join(symbols), DMClient.__date2str(start_date), DMClient.__date2str(end_date)])
        res = self.__request('is_suspended', args)
        res_map = {}
        for r in res['is_suspended']:
            if r['time'] not in res_map:
                res_map[r['time']] = {}
            res_map[r['time']][r['symbol']] = r['suspended']
        return pandas.DataFrame(res_map)

    def get_index_component(self, index, date):
        self.__refresh_token_if_needed()
        args = DMClient.__compact_to_map(
                ['index', 'date'],
                [index, DMClient.__date2str(date)])
        res = self.__request('index_components', args)
        return pandas.DataFrame([{'symbol': r['symbol'], 'weight': r['weight']} for r in res['index_components']])

    def get_industry_category(self, industry_type, level='ALL'):
        self.__refresh_token_if_needed()
        args = DMClient.__compact_to_map(
                ['industry_type', 'level'],
                [industry_type, level])
        res = self.__request('industry_category', args)
        return pandas.DataFrame(res)

    def get_instruments_industry(self, industry_code, level, date=None):
        self.__refresh_token_if_needed()
        if date is not None:
            date = DMClient.__date2str(date)
        args = DMClient.__compact_to_map(
                ['industry_codes', 'level', 'date'],
                [industry_code, level, date])
        res = self.__request('instruments_of_industry', args)
        if industry_code in res:
            return pandas.DataFrame(res[industry_code])
        else:
            return pandas.DataFrame()

    def get_dominant_contract(self, varieties, start_date, end_date):
        self.__refresh_token_if_needed()
        args = DMClient.__compact_to_map(
                ['varieties', 'start_date', 'end_date'],
                [','.join(varieties), DMClient.__date2str(start_date), DMClient.__date2str(end_date)])
        res = self.__request('dominant_contract', args)
        return pandas.DataFrame(res['domain_contracts'])

    def get_trading_time(self, varieties, date):
        self.__refresh_token_if_needed()
        args = DMClient.__compact_to_map(
                ['varieties', 'date'],
                [','.join(varieties), DMClient.__date2str(date)])
        res = self.__request('trading_time', args)
        return pandas.DataFrame([{'variety': k, 'start_time': v['start_time'], 'end_time': v['end_time']} for k, v in res.items()])

    def get_exchange_time(self, exchange, date):
        self.__refresh_token_if_needed()
        args = DMClient.__compact_to_map(
                ['exchange', 'date'],
                [exchange, DMClient.__date2str(date)])
        res = self.__request('trading_time', args)
        return pandas.DataFrame([{'exchange': v['exchange'], 'start_time': v['start_time'], 'end_time': v['end_time']} for k, v in res.items()])


