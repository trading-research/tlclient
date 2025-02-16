# auto generated by update_py.py

import functools
import os
import datetime
import traceback

from tlclient.linker.logger import Logger


def singleton(cls, *args, **kwargs):
    instances = {}

    def getInstance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return getInstance


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


def handle_exception(func):

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            func(self, *args, **kwargs)
        except Exception as e:
            info = f'{func.__name__} failed! going to stop myself... (err_info){e}'
            self.logger.exception(info)
            with open(os.path.join(Logger._get_log_path_from_env(), self.fist_name + '_err.log'), mode='a') as f:
                f.writelines((str(datetime.datetime.now()) + ' ' + info, '\n'))
                traceback.print_exc(file=f)
            self.stop(-1)

    return wrapper
