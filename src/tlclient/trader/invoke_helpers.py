# auto generated by update_py.py

import os
import sys
import time
import zmq


class InvokeBase:

    ERROR_SIGN = 1
    INFO_SIGN = 0
    STOP_SIGN = 2

    @staticmethod
    def get_ipc_addr(config_file_path):
        return 'ipc://{}/_invoke.sock'.format(os.path.dirname(os.path.abspath(config_file_path)))


class InvokeServer(InvokeBase):

    def __init__(self, addr):
        context = zmq.Context()
        self.socket = context.socket(zmq.SUB)
        self.socket.setsockopt(zmq.SUBSCRIBE, b'')
        self.socket.setsockopt(zmq.SNDHWM, 0)
        self.socket.setsockopt(zmq.RCVHWM, 0)
        self.socket.bind(addr)
        self.errors = []
        self.infos = []
        self.result = True

    def print_out(self):
        print('|------ error ----')
        for (t, e) in self.errors:
            print('| {} - {}'.format(t, e))
        print('|------ info -----')
        for (t, e) in self.infos:
            print('| {} - {}'.format(t, e))
        print('|-----------------')
        print('| {} info, {} error '.format(len(self.infos), len(self.errors)))
        print('|-----------------')

    def run(self):
        print('|--- INVOKE SERVER ---')
        to_stop = False
        while not to_stop:
            raw_msg = self.socket.recv().decode('utf8')
            print('| ' + raw_msg)
            sign = int(raw_msg[0])
            content = raw_msg[2:].encode('utf8') if sys.version_info.major == 2 else raw_msg[2:]
            if sign == self.STOP_SIGN:
                to_stop = True
            elif sign == self.INFO_SIGN:
                self.infos.append((time.strftime('%H:%M:%S'), content))
            elif sign == self.ERROR_SIGN:
                self.errors.append((time.strftime('%H:%M:%S'), content))
        print('|')
        self.print_out()
        self.result = len(self.errors) == 0
        return self.result

class InvokeClient(InvokeBase):

    def __init__(self, addr):
        context = zmq.Context()
        self.socket = context.socket(zmq.PUB)
        self.socket.setsockopt(zmq.SNDHWM, 0)
        self.socket.setsockopt(zmq.RCVHWM, 0)
        self.socket.connect(addr)

    def _send(self, msg):
        msg_to_send = msg.decode('utf8') if sys.version_info.major == 2 else msg
        self.socket.send_string(msg_to_send)

    def info(self, msg):
        self._send('{} {}'.format(self.INFO_SIGN, msg))

    def error(self, msg):
        self._send('{} {}'.format(self.ERROR_SIGN, msg))

    def stop(self):
        self._send('{} {}'.format(self.STOP_SIGN, ''))
