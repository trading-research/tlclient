# auto generated by update_py.py

import copy
import datetime
import json
import os
import sys
import time
import typing

from typing import Optional
from collections import OrderedDict, defaultdict
from functools import reduce
from importlib import import_module

from tlclient.linker.constant import MASTER_FIST_NAME, FistType
from tlclient.linker.event import Event
from tlclient.linker.fist import Fist
from tlclient.linker.frame import Frame
from tlclient.linker.logger import Logger
from tlclient.linker.pb_msg import comm_pb, frame_pb
from tlclient.linker.timer import Timer
from tlclient.linker.utility import bytify
from tlclient.trader.config import Configurator
from tlclient.trader.notification import NotificationCenter
from tlclient.trader.oms import OrderManagerService
from tlclient.trader.param_server import ParamServer
from tlclient.trader.recorder import Recorder
from tlclient.trader.next_oms import NextOMS

FIST_READY_MARK = '$FIST_READY$'
FIST_FAIL_MARK = '$FIST_FAIL$'

CONFIG_FOLDER = '/shared/etc'
CONFIG_DEFAULT_PATH = '{}/config.json'.format(CONFIG_FOLDER)

DEFAULT_LATEST_CONFIG_VERSION = "0.3"


class GUN_FALGS(object):
    DISABLE_CONSOLE_LOGGER = False


def print_fist_ready_mark():
    print(FIST_READY_MARK)
    sys.stdout.flush()

    if GUN_FALGS.DISABLE_CONSOLE_LOGGER:
        print('redirecting console logger to /dev/null...')
        sys.stdout.flush()
        Logger.redirect_console_handler_to_DEVNULL()


def print_fist_fail_mark():
    print(FIST_FAIL_MARK)
    sys.stdout.flush()


class GunStartHelper(object):

    proc_types = {
        FistType.MARKET_GATEWAY: 'mg',
        FistType.TRADE_GATEWAY: 'tg',
        FistType.MARKET_ROUTER: 'mr',
        FistType.TRADE_ROUTER: 'tr',
        FistType.ORDER_MANAGER: 'oms',
        FistType.RISK_MANAGER: 'rms',
        FistType.BASKET_SERVER: 'bs',
        FistType.ALGO_SERVER: 'algo',
        FistType.RECORDER: 'rr',
        FistType.PARAM_SERVER: 'pp',
    }

    @classmethod
    def to_proc_type(cls, fist_type):
        fist_type_code = FistType.parse(fist_type)
        return cls.proc_types.get(fist_type_code)

    @classmethod
    def to_gun_start_cmd(cls, config):
        fist_name = config.get('fist_name')
        fist_type = cls.to_proc_type(config.get('fist_type'))
        assert None not in [fist_name, fist_type], 'None fist type or fist name (type/name){}/{}'.format(fist_type, fist_name)

        cmd = 'gun start -t {} -f {} -d '.format(fist_type, fist_name)
        if fist_name is not None:
            cmd += '-a {} '.format(fist_name)
        gateway_name = config.get('gateway_name')
        if gateway_name is not None:
            cmd += '-g {} '.format(gateway_name)
        router_name = config.get('router_name')
        if router_name is not None:
            cmd += '-r {} '.format(router_name)
        package_name = config.get('package_name')
        if package_name is not None:
            cmd += '-p {} '.format(package_name)

        return cmd


class GunClientHelper(object):

    def __init__(self, fist_name, config_path=None, env_name=None, master_addr=None):
        j = json.load(open(config_path))
        if env_name is None or master_addr is None:
            # init recorder
            master_addr = j['master_rep']

        curve_server_key = j.get('curve_server_key', '')
        self.fist_client = Fist(fist_name, FistType.BASE, '--', master_addr, curve_server_key=curve_server_key)
        self.fist_client.reg_req_master()
        # force to set LINGER=0
        import zmq
        self.fist_client.req_socks[MASTER_FIST_NAME].setsockopt(zmq.LINGER, 0)

    def stop(self, fist_name):
        req = comm_pb.ReqFistSuicide()
        req.fist_name = fist_name
        f = Event.new_pb_frame()
        f.set_msg_type(frame_pb.MsgType.MSG_TYPE_CMD_SUICIDE)
        f.set_nano(Timer.nano())
        f.set_data(req)
        try:
            self.fist_client.req_master(f)
        except:
            pass

    def get_status(self):
        f = Event.new_pb_frame()
        f.set_msg_type(frame_pb.MsgType.MSG_TYPE_GET_STATUS)
        f.set_nano(Timer.nano())
        rsp = self.fist_client.req_master(f)
        return rsp.get_string()

    def join(self, fist_name, join_wait_seconds):
        is_running = True
        try:
            while is_running:
                is_running = False
                js = json.loads(self.get_status())
                for item in js:
                    if fist_name == item['fist_name'] and item['is_running']:
                        time.sleep(join_wait_seconds)
                        is_running = True
                        break
            print('{} is not running'.format(fist_name))
        except:
            print('master invalid')


class ConfigHelper(object):

    def __init__(self, config_dir=CONFIG_FOLDER, latest_config_version=DEFAULT_LATEST_CONFIG_VERSION):
        self.latest_config_version = latest_config_version
        self.config_dir = config_dir
        self.config_path = os.path.join(config_dir, 'config.json')

        self.config = None
        self.load_config()
        self.current_config_version = self.config.get("config_version", "0.1")
        self.current_backup_path = None

    def _print_and_run_sys_cmd(self, cmd):
        print(cmd)
        os.system(cmd)

    def backup_config(self):
        backup_path = os.path.join(self.config_dir, 'config.json.bak.{}'.format(len(os.listdir(self.config_dir))))
        cmd = "cp {} {}".format(self.config_path, backup_path)
        self._print_and_run_sys_cmd(cmd)
        self.current_backup_path = backup_path

    def _extract_port(self, addr):
        return int(addr.split(':')[-1])

    def _update_config_0_1(self, config):
        config['config_version'] = '0.2'
        config['master_rep_port'] = self._extract_port(config["master_rep"])
        config['master_rep'] = "tcp://127.0.0.1:{}".format(config['master_rep_port'])
        config['env'] = 'env1'
        config["env_infos"] = [
            {
                "env_name": "env1",
                "private_ip": "192.168.108.177",
                "public_ip": "36.110.14.214"
            },
            {
                "env_name": "env2",
                "private_ip": "192.168.108.177",
                "public_ip": "36.110.14.214"
            }
        ]
        for module in config['modules']:
            for comm_type, value in module['addrs'].items():
                if value.startswith("tcp"):
                    module['addrs'][comm_type] = {
                        'comm_method': "TCP",
                        "port": self._extract_port(value)
                    }
                else:
                    print('[ERROR] unhandled addr (key){} (value){}'.format(comm_type, value))

    def _update_config_0_2(self, config):
        config['config_version'] = '0.3'
        new_accounts = {
            'ctp_test': {
                'gateway_name': 'ctp',
                'gateway_type': 'TRADE_GATEWAY'
            },
            'ctp1': {
                'gateway_name': 'ctp',
                'gateway_type': 'MARKET_GATEWAY'
            }
        }
        for gw_name, gw_accounts in config['accounts'].items():
            for acc_tag, acc_info in gw_accounts.items():
                new_acc_tag = acc_tag
                while new_acc_tag in new_accounts:
                    new_acc_tag += "1"
                new_accounts[new_acc_tag] = acc_info
                new_accounts[new_acc_tag]['gateway_name'] = gw_name
                new_accounts[new_acc_tag]['gateway_type'] = 'MARKET_GATEWAY' if 'market' in new_acc_tag or 'qts' in new_acc_tag else 'TRADE_GATEWAY'
        config['accounts'] = new_accounts

    def update_config(self):
        if self.current_config_version == self.latest_config_version:
            print('already in latest version: {}'.format(self.latest_config_version))
            if self.current_backup_path is not None:
                os.remove(self.current_backup_path)
                print('removed backup file {}'.format(self.current_backup_path))
                self.current_backup_path = None
        while self.current_config_version != self.latest_config_version:
            print('current_version: {}'.format(self.current_config_version))
            eval('self._update_config_{}(self.config)'.format(self.current_config_version.replace('.', '_')))
            self.current_config_version = self.config['config_version']

    def load_config(self):
        self.config = json.load(open(self.config_path))

    def dump_config(self):
        json.dump(self.config, open(self.config_path, "w+"), indent=4)

    def check_version(self):
        if self.current_config_version != self.latest_config_version:
            print("[ERROR] outdated config version: {}. the latest version is {}".format(self.current_config_version, self.latest_config_version))
            return False
        else:
            print("already in latest version {}".format(self.current_config_version))
            return True

    def get_master_rep_addr(self):
        return self.config['master_rep']

    def get_http_proxy_addr(self):
        return self.config.get('http_proxy')

    def open_config_to_edit(self):
        import subprocess
        print('{0} [Edit Config - {1}] {0}'.format('*' * 50, self.config_path))
        # edit config as file, quit if not modified
        before_mdf_time = os.path.getmtime(self.config_path)
        editor = os.environ.get('EDITOR', 'vim')
        subprocess.call([editor, self.config_path])
        if os.path.getmtime(self.config_path) == before_mdf_time:
            print('>>>>>>>>>', 'config not saved...')
        else:
            print('>>>>>>>>>', 'config saved!')

    def get_acc_config(self, acc_tag):
        if 'accounts' not in self.config or acc_tag not in self.config['accounts']:
            return None
        return self.config['accounts'][acc_tag]


class LogHelper(object):

    def __init__(self, paths):
        self.paths = paths or [Logger._get_log_path_from_env()]

    def _get_log_files(self, path):
        return [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f)) and (f.endswith('.txt') or '.log' in f)]

    def _get_fist_files(self, path, fist_name):
        fist_files = []
        for f in self._get_log_files(path):
            f_name = f.split('_')[0] if f.endswith('.txt') else f.split('.log')[0]
            if f_name == fist_name:
                f_path = os.path.join(path, f)
                fist_files.append((f_path, os.stat(f_path).st_ctime))

        return fist_files

    def _get_expired_files(self, path, expired_time):
        file_names = []
        now = datetime.datetime.now()

        for f in self._get_log_files(path):
            last_modified_time = datetime.datetime.fromtimestamp(os.stat(os.path.join(path, f)).st_ctime)
            if (now - last_modified_time).days >= expired_time:
                file_names.append(f)

        return file_names

    def _clean_expired_files(self, path, file_names):
        for f in file_names:
            os.remove(os.path.join(path, f))

    def _get_fist_names(self, path):
        fist_names = set()
        for f in self._get_log_files(path):
            f_name = f.split('_')[0] if f.endswith('.txt') else f.split('.log')[0]
            fist_names.add(f_name)

        return fist_names

    def tail_latest_log(self, fist_name):
        files = []
        for path in self.paths:
            files.extend(self._get_fist_files(path, fist_name))
        if len(files) == 0:
            print('[ERROR] could not find "{}" log in {}'.format(fist_name, self.paths))
        else:
            latest_log = max(files, key=lambda f: f[1])[0]
            from sh import tail
            try:
                for line in tail("-f", latest_log, _iter=True):
                    print(line, end='')
            except KeyboardInterrupt:
                print()

    def clean_expired_log(self, expired_time):
        for path in self.paths:
            file_names = self._get_expired_files(path, expired_time)
            if len(file_names) > 0:
                self._clean_expired_files(path, file_names)
            print('(path){} (file_count){}:\n{}'.format(path, len(file_names), '\t'.join(file_names)))

    def show_fist_list(self):
        for path in self.paths:
            fist_names = self._get_fist_names(path)
            print('(path){} (fist_count){}:\n{}'.format(path, len(fist_names), '\t'.join(fist_names)))

# FISTS


class Router(object):

    def __init__(self, tag, fist_name):
        import libtrader
        if tag == 'tr':
            fist_name = fist_name or 'trade1'
            self._obj = libtrader.TradeRouter(fist_name)
        elif tag == 'mr':
            fist_name = fist_name or 'market1'
            self._obj = libtrader.MarketRouter(fist_name)
        else:
            raise Exception("unexpected tag: " + tag)
        self._obj.init()

    def run(self):
        self._obj.start()
        print_fist_ready_mark()
        self._obj.join()


class Gateway(object):

    def __init__(self, gw_tag, gw_name, acc_tag, router_name, oms_name, record_order, secondary_router_name=None):
        import libtrader
        assert acc_tag is not None, 'must specify acc tag'
        assert gw_tag in ["tg", "mg"], "unexpected gateway tag" + gw_tag
        if gw_tag == 'tg' and gw_name == 'mock':
            router_name = router_name or 'trade1'
            secondary_router_name = secondary_router_name or 'market1'
            self._obj = libtrader.MockGateway(acc_tag)
            self._obj.init_market(secondary_router_name)
        elif gw_tag == 'mg' and gw_name == 'replay':
            router_name = router_name or 'market1'
            self._obj = libtrader.ReplayGateway(acc_tag)
        else:
            router_name = router_name or ('trade1' if gw_tag == 'tg' else 'market1')
            lib_name = 'lib{}{}'.format(gw_tag, gw_name)
            imported_lib = None
            try:
                imported_lib = __import__(lib_name)
                globals()[lib_name] = imported_lib
            except Exception:
                raise Exception("cannot find lib named {}".format(lib_name))
            self._obj = imported_lib.Gateway(acc_tag)

        self._obj.set_account()
        self._obj.init(router_name, record_order, True)
        if gw_tag == 'tg' and oms_name:
            self._obj.init_oms(oms_name)

    def run(self):
        self._obj.start()
        print_fist_ready_mark()
        self._obj.join()


class PythonGateway(object):

    def __init__(self, package_name, gw_tag, gw_name, router_name, oms_name, acc_tag=None, fist_name=None, use_proxy=False, from_json=False, sub_config=None):
        assert gw_tag in ['tg', 'mg'], 'unexpected gateway tag ' + gw_tag

        self.gw_tag = gw_tag
        self.subscribe_config = {}
        class_name = gw_name.title().replace('_', '')
        master_addr = ConfigHelper().get_master_rep_addr()
        if gw_tag == 'mg':
            class_name += 'MarketGateway'
            kwargs = {
                'fist_name': fist_name or '{}_{}'.format(gw_tag, gw_name),
                'mrouter_name': router_name or 'market1',
                'addr': master_addr,
            }

            if isinstance(sub_config, list):
                for arg in sub_config:
                    key, value = arg.split(':')
                    if key in ['trade', 'snap', 'bar']:
                        self.subscribe_config[key] = value.split(',')
                    else:
                        print('[gun] sub config key only support ["trade", "snap", "bar"], unsupport "{}"'.format(key))

        elif gw_tag == 'tg':
            assert acc_tag is not None, 'could not find acc_tag in command'
            if from_json:
                acc_config = ConfigHelper().get_acc_config(acc_tag)
                assert acc_config is not None, 'could not find account config in config file'
            else:
                from .helpers import AccountHelper
                # get account config from db
                account = AccountHelper().get_account(acc_tag)
                assert account is not None, 'could not find account config in db'
                acc_config = account.get_decrypted_acc_config()
            # prep tg args
            class_name += 'TradeGateway'
            acc_tag = fist_name or acc_tag
            kwargs = {
                'acc_tag': acc_tag,
                'acc_config': acc_config,
                'router_name': router_name or 'trade1',
                'oms_name': oms_name,
                'addr': master_addr,
            }

        if use_proxy:
            proxy_config = ConfigHelper().get_http_proxy_addr()
            kwargs['proxy_config'] = proxy_config
            print('[gun] using proxy config {}'.format(proxy_config))

        # get env config
        env_setting = Configurator().get_env_settings()
        kwargs['env_name'] = env_setting.env_name
        kwargs['addr'] = env_setting.master_addr

        mylib = __import__(package_name)
        self.obj = eval('mylib.{}(**kwargs)'.format(class_name))

    def run(self):
        self.obj.start()
        print_fist_ready_mark()
        if self.gw_tag == 'mg' and self.subscribe_config:
            self.obj.init_subscribe(self.subscribe_config)
        self.obj.join()


class GunOrderManagerService(object):

    def __init__(self, fist_name=None, router_name=None):
        j = json.load(open(CONFIG_DEFAULT_PATH))

        fist_name = fist_name or 'oms1'
        env_name = j['env']
        master_addr = j['master_rep']
        db_path = j['sqlite']

        router_name = router_name or 'trade1'
        self._obj = OrderManagerService(fist_name, env_name, master_addr, db_path)
        self._obj.init_trade(router_name)

    def run(self):
        self._obj.start()
        print_fist_ready_mark()
        self._obj.join()


class RiskManagementService(object):

    def __init__(self, fist_name=None, router1=None):
        fist_name = fist_name or 'rms1'
        router1 = router1 or 'trade1'

        import libtrader
        self._obj = libtrader.RiskManager(fist_name)
        self._obj.init(router1)

    def run(self):
        self._obj.start()
        print_fist_ready_mark()
        self._obj.join()


class BasketServer(object):

    def __init__(self, fist_name=None, trade_router=None):
        fist_name = fist_name or 'basket'
        trade_router = trade_router or 'trade1'

        import libtrader
        self._obj = libtrader.BasketServer(fist_name)
        self._obj.init_trade(trade_router)

    def run(self):
        self._obj.start()
        print_fist_ready_mark()
        self._obj.join()


class AlgoServer(object):

    def __init__(self, algo_type, trade_router=None, market_router=None):
        assert algo_type is not None, 'must specify algo type'
        trade_router = trade_router or 'trade1'
        market_router = market_router or 'market1'

        lib_name = 'libalgo{}'.format(algo_type)
        imported_lib = __import__(lib_name)
        globals()[lib_name] = imported_lib
        self._obj = imported_lib.AlgoServer()
        self._obj.init_trade(trade_router)
        self._obj.init_market(market_router)

    def run(self):
        self._obj.start()
        print_fist_ready_mark()
        self._obj.join()


class GunRecorder(object):

    def __init__(self, fist_name, router_names, csv_dir=None, kdb_host=None, kdb_port=None, influx_host=None, influx_port=None, influx_udp_port=None, *, mongo_collection=None, mongo_db_name=None):
        j = json.load(open(CONFIG_DEFAULT_PATH))
        # init recorder
        env_name = j['env']
        master_addr = j['master_rep']
        self._obj = Recorder(fist_name or 'recorder', env_name, master_addr)
        # set routers
        router_names = router_names or ['market1', 'trade1']
        for router_name in router_names:
            self._obj.sub_router(router_name)
        # set csv dumper
        if csv_dir:
            self._obj.add_csv_client(path=csv_dir)
        if kdb_host and kdb_port:
            self._obj.add_kdb_client(host=kdb_host, port=kdb_port)
        if influx_host and influx_port:
            self._obj.add_influxdb_client(host=influx_host, port=influx_port, udp_port=influx_udp_port)
        if mongo_collection is not None:
            config_path = CONFIG_DEFAULT_PATH if 'MONGO_CONFIG_PATH' not in os.environ else os.environ['MONGO_CONFIG_PATH']
            self._obj.add_mongo_client(config_path, mongo_collection, db_name=mongo_db_name)
        # set db
        ''' we temp remove influxdb related
        if 'influxdb' in j:
            influx_db_info = j['influxdb']
            _info = influx_db_info[influx_db_info['mode']]
            self._obj.set_influxdb(host=_info['host'],
                                   port=_info['port'],
                                   user=_info['username'],
                                   passwd=_info['password'],
                                   db=_info['db'])
        '''

    def run(self):
        self._obj.start()
        print_fist_ready_mark()
        self._obj.join()


class GunNotificationCenter(object):

    def __init__(self, fist_name, wxwork_url=None):
        j = json.load(open(CONFIG_DEFAULT_PATH))
        # init notification
        env_name = j['env']
        master_addr = j['master_rep']
        redis_config = j['notification_center']['redis']
        self._obj = NotificationCenter(fist_name or 'notification', env_name, master_addr, redis_config['host'],
                                       redis_config['port'], redis_config['password'], redis_config['key'])
        # set wxwork
        if wxwork_url:
            self._obj.add_wxwork_client(wxwork_url)

    def run(self):
        self._obj.start()
        print_fist_ready_mark()
        self._obj.join()


class GunParamServer():

    def __init__(self, fist_name: str, files_path: str):
        j = json.load(open(CONFIG_DEFAULT_PATH))
        self._obj = ParamServer(fist_name or 'param server', j['env'], j['master_rep'], files_path)
        self._obj.init()

    def run(self):
        self._obj.start()
        print_fist_ready_mark()
        self._obj.join()


class GunTunnelPeer:

    def __init__(self, fist_name: str, gateway_name: str, config_file_path: str):
        lib_name = f'lib{gateway_name}_tunnel'
        imported_lib = None
        try:
            imported_lib = import_module(lib_name)
            # globals()[lib_name] = imported_lib
        except Exception:
            raise Exception("cannot find lib named {}".format(lib_name))
        self._obj = imported_lib.TunnelClient(fist_name, config_file_path)
        # self._obj.init_trade(trade_router)
        # self._obj.init_market(trade_router)

    def run(self):
        self._obj.start()
        print_fist_ready_mark()
        self._obj.join()


class GunNextOMS:

    def __init__(self, data_impl_pkg: Optional[str], fist_name: Optional[str], trade_router, market_router):
        self._obj = NextOMS(data_impl_pkg if data_impl_pkg is not None else 'oms', fist_name)
        self._obj.init(trade_router, market_router)

    def run(self):
        self._obj.start()
        print_fist_ready_mark()
        self._obj.join()


class CmdFist(Fist):

    def __init__(self, fist_name):
        j = json.load(open(CONFIG_DEFAULT_PATH))
        # init fist
        env_name = j['env']
        master_addr = j['master_rep']
        curve_server_key = j.get('curve_server_key', '')
        Fist.__init__(self, fist_name, FistType.TEST, env_name, master_addr, curve_server_key=curve_server_key)
        self.rsps = {}

    def on_rsp_command(self, request_id, from_fist_name, content):
        self.rsps[request_id] = content

    def has_rsp(self, request_id):
        return request_id in self.rsps

    def get_rsp(self, request_id, timeout=-1):
        assert request_id is not None and request_id > 0
        assert timeout == -1 or timeout > 0

        waited_time = 0
        rsp = None
        while True:
            if (timeout != -1 and waited_time >= timeout) \
                    or self.is_stopped():
                print('[error] cmd timeout')
                break
            rsp = self.rsps.get(request_id)
            if rsp:
                break
            time.sleep(0.1)
            waited_time += 0.1

        return rsp


class EnvHelper(object):

    def __init__(self):
        pass

    @staticmethod
    def get_env_name():
        config = json.load(open(CONFIG_DEFAULT_PATH))
        assert 'env' in config, 'env name not set'
        env_name = config['env']
        return env_name

    @staticmethod
    def set_current_env_name(env_name):
        config = json.load(open(CONFIG_DEFAULT_PATH))
        config['env'] = env_name
        json.dump(config, open(CONFIG_DEFAULT_PATH, 'w+'), indent=2)
        print('[env] set env name "{}"'.format(env_name))

    @staticmethod
    def register_env_info(env_info):
        f = Event.new_pb_frame()
        f.set_msg_type(frame_pb.MsgType.MSG_TYPE_ENV_INFO_UPDATE)
        f.set_string(json.dumps(env_info.to_dict()))
        cmd = CmdFist('__register_env')
        cmd.create_fist()
        res = cmd.req_master(f)
        print('[env] sent update (env){} (res){}'.format(env_info, res.get_err_id() == 0))


class GunInspector(object):

    OPTION_ENVS = 'envs'
    OPTION_FISTS = 'fists'

    def __init__(self):
        env_config = Configurator().get_env_settings()
        self._fist = Fist('_gun_inspector', FistType.NOT_AVAILABLE, env_config.env_name, env_config.master_addr)
        self._fist.logger.disabled = True
        self._fist.create_fist()
        self._status = None
        self.update_status()

    def update_status(self):
        f = Event.new_pb_frame()
        f.set_msg_type(frame_pb.MsgType.MSG_TYPE_GET_FULL_STATUS)
        rsp_f = self._fist.req_master(f)
        assert rsp_f.get_err_id() == 0
        self._status = json.loads(rsp_f.get_string())

    def get_current_status(self):
        return self._status

    def pretty_print(self, data: typing.List[typing.Dict], headers=None):
        import tabulate

        if not len(data):
            print('(empty)')
            return

        headers = headers or 'keys'
        print(tabulate.tabulate(data, headers=headers, tablefmt='simple'))

    def restrucure_data(self, data, **kwargs):
        if not data:
            return data
        data = copy.deepcopy(data)

        # group by
        group_by = kwargs.get('group_by')
        data_groups = []
        if group_by:
            assert group_by in data[0].keys(), 'invalid group_by value "{}"'.format(group_by)
            temp = defaultdict(list)
            for d in data:
                temp[d[group_by]].append(d)
            data_groups = list(temp.values())
        else:
            data_groups = [data]
        # sort
        sort_by = kwargs.get('sort_by')
        reverse = kwargs.get('reverse')
        for group in data_groups:
            if sort_by:
                assert sort_by in group[0].keys(), 'invalid sort_by value "{}"'.format(sort_by)
                group.sort(key=lambda x: x[sort_by], reverse=reverse)
            if group_by:
                group.insert(0, {group_by: 'group: ' + str(group[0][group_by])})
                for d in group[1:]:
                    d[group_by] = ''
                group.append({})
        data = reduce(lambda x, y: x+y, data_groups)

        return data

    def inspect_envs(self, **kwargs):
        curr_env = self._fist.env_name
        env_infos = list(self._status['envs'].values())
        for env_info in env_infos:
            if env_info['env_name'] == curr_env:
                env_info['env_name'] += ' *'
                print('(current env name is suffixed with "*")')
        data = self.restrucure_data(env_infos, **kwargs)
        self.pretty_print(data)

    def inspect_fists(self, **kwargs):
        fist_infos = self._status['fists']
        data = []
        for fi in fist_infos:
            start_time = datetime.datetime.fromtimestamp(fi['start_nano'] / 1e9).strftime('%Y%m%d-%H:%M:%S') if fi['start_nano'] else '-'
            end_time = datetime.datetime.fromtimestamp(fi['end_nano'] / 1e9).strftime('%Y%m%d-%H:%M:%S') if fi['end_nano'] else '-'
            fist_type = FistType.read(fi['fist_type']) or '-'
            data.append(
                OrderedDict(
                    [
                        ('sid', fi['source_id']),
                        ('env', fi['env_name']),
                        ('name', fi['fist_name']),
                        ('type', fist_type),
                        ('running', fi['is_running']),
                        ('pid', fi['pid']),
                        ('start_time', start_time),
                        ('end_time', end_time),
                    ]
                )
            )
        data = self.restrucure_data(data, **kwargs)
        self.pretty_print(data)

    def inspect(self, option, **kwargs):
        if option == self.OPTION_ENVS:
            self.inspect_envs(**kwargs)

        elif option == self.OPTION_FISTS:
            self.inspect_fists(**kwargs)

        else:
            raise NotImplementedError()

    @staticmethod
    def get_options():
        return [
            GunInspector.OPTION_ENVS,
            GunInspector.OPTION_FISTS
        ]
