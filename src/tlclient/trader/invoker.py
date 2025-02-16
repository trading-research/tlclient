# auto generated by update_py.py

import argparse
import colorama
import json
import liblinker
import libtrader
import multiprocessing
import os
import subprocess
import sys
import threading
import time

from tlclient.linker.constant import FistType
from tlclient.trader.gun_helpers import GunClientHelper
from tlclient.trader.invoke_helpers import InvokeServer



def process_module(m, config_path=None):
    if config_path:
        liblinker.set_config_path(config_path)
        os.chdir(os.path.dirname(config_path))
        config_path = os.path.join(os.getcwd(), os.path.basename(config_path))

    # logic
    ft = FistType.parse(m['fist_type'])
    fn = m['fist_name']
    obj = None
    if ft == FistType.MASTER:
        obj = liblinker.Master()
    elif ft == FistType.MARKET_ROUTER:
        obj = libtrader.MarketRouter(fn)
        obj.init()
    elif ft == FistType.TRADE_ROUTER:
        obj = libtrader.TradeRouter(fn)
        obj.init()
    elif ft == FistType.ORDER_MANAGER:
        from .gun_helpers import GunOrderManagerService
        obj = GunOrderManagerService()
        obj.run()
        return
    elif 'cmd' in m:
        cmd = m['cmd']
        if '$CONFIG_PATH' in cmd:
            cmd = cmd.replace('$CONFIG_PATH', config_path)
        os.system(cmd)
    else:
        print('[error] unrecognized fist type "{}"'.format(ft))

    if obj:
        obj.start()
        obj.join()


def run_module(m, config_path=None):
    p = multiprocessing.Process(target=process_module, args=[m, config_path])
    p.daemon = True
    p.start()
    try:
        p.join()
    except KeyboardInterrupt:
        pass


def start_module(m, config_path=None):
    cmd = 'python3 -m trader.invoker -f {} -s {}'.format(config_path, m['source_id'])
    print(cmd)
    subprocess.Popen(cmd, shell=True, stderr=subprocess.STDOUT)


def run_invoke(argvs):
    main_parser = argparse.ArgumentParser(description='invoker help')
    main_parser.add_argument('-f', '--config_file', help='config file path')
    main_parser.add_argument('-s', '--source_id', help='source id to run')
    main_parser.add_argument('-t', '--run_type', help='run/stop/status')
    main_parser.add_argument('-i', '--sec_interval', help='seconds to sleep')
    args = main_parser.parse_args(argvs)

    config_path = args.config_file
    source_id = args.source_id
    sec_interval = args.sec_interval if args.sec_interval else 1
    run_type = 'run' if args.run_type is None else args.run_type

    if run_type == 'stop':
        helper = GunClientHelper('__killer', config_path)
        helper.stop('master')

    elif run_type == 'run':
        config = json.load(open(config_path))
        if source_id == None:
            # build up our server
            ipc_addr = InvokeServer.get_ipc_addr(config_path)
            print('listening to: ' + ipc_addr)
            sver = InvokeServer(ipc_addr)
            th = threading.Thread(target=sver.run)
            th.daemon = True
            th.start()
            for m in config["modules"]:
                start_module(m, config_path)
                time.sleep(sec_interval)
            print('waiting....')
            th.join()
            print(colorama.Back.GREEN if sver.result else colorama.Back.RED)
            print('''
-----------------------------------
|             {}                |
-----------------------------------
            '''.format('PASS' if sver.result else 'FAIL'))
            print(colorama.Style.RESET_ALL)
            helper = GunClientHelper('__killer', config_path)
            helper.stop('master')
        else:
            for m in config["modules"]:
                if m['source_id'] == int(source_id):
                    run_module(m, config_path)

    elif run_type == 'status':
        os.system('linker_status by ' + config_path)

    else:
        print('unexpected run_type: {}'.format(run_type))


if __name__ == '__main__':
    run_invoke(sys.argv[1:])
