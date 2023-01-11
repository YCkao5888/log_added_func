import logging
import logging.handlers
from concurrent_log_handler import ConcurrentRotatingFileHandler
import os

import psutil
from psutil._common import bytes2human


class CustomFormatter(logging.Formatter):
    """ Custom Formatter does these 2 things:
    1. Overrides 'funcName' with the value of 'func_name_override', if it exists.
    2. Overrides 'filename' with the value of 'file_name_override', if it exists.
    """

    def format(self, record):
        if hasattr(record, 'func_name_override'):
            record.funcName = record.func_name_override
        if hasattr(record, 'file_name_override'):
            record.filename = record.file_name_override
        return super(CustomFormatter, self).format(record)


old_factory = logging.getLogRecordFactory()
def system_info_factory(*args, **kwargs):
    record = old_factory(*args, **kwargs)
    mem = psutil.virtual_memory()
    cpu_percent = psutil.cpu_percent(percpu=True)  # get a list represent cpu usages

    record.mem_percent = mem.percent
    # record.cpu_percent1, record.cpu_percent2, record.cpu_percent3, record.cpu_percent4 = cpu_percent
    return record


def get_logger(log_file_name='main_log', log_sub_dir=""):
    """ Creates a Log File and returns Logger object """

    windows_log_dir = 'c:\\logs_dir\\'
    linux_log_dir = './logs_dir/'

    # Build Log file directory, based on the OS and supplied input
    log_dir = windows_log_dir if os.name == 'nt' else linux_log_dir
    log_dir = os.path.join(log_dir, log_sub_dir)

    # Create Log file directory if not exists
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Build Log File Full Path
    logPath = log_file_name if os.path.exists(log_file_name) else os.path.join(log_dir, (str(log_file_name) + '.log'))

    # Create logger object and set the format for logging and other attributes
    logger = logging.Logger(log_file_name)
    logging.setLogRecordFactory(system_info_factory)
    logger.setLevel(logging.DEBUG)  #　DEBUG等級以上的會進行處理 => 也就是全部都會處理
    #handler = logging.FileHandler(logPath, 'a+')
    handler = ConcurrentRotatingFileHandler(logPath, maxBytes=50 * 1024 * 1024, backupCount=2)  #  1 * 1024 * 1024 = 1MB
    #handler = logging.handlers.RotatingFileHandler(logPath, maxBytes=1 *  1024, backupCount=1)
    """ Set the formatter of 'CustomFormatter' type as we need to log base function name and base file name """
    handler.setFormatter(CustomFormatter('%(asctime)s $ %(levelname)-10s $ %(mem_percent).1f $%(threadName)s $ %(filename)s $ %(funcName)s $ %(message)s'))
    logger.addHandler(handler)

    # Return logger object
    return logger
