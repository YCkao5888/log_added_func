import logging
import logging.handlers
from concurrent_log_handler import ConcurrentRotatingFileHandler
import os

import psutil
from psutil._common import bytes2human

import atexit
import glob
import signal
import time


def _read_pid_from_lock(lock_path: str) -> int | None:
    """嘗試從 lock 檔讀取 PID；若無法解析則回傳 None。"""
    try:
        with open(lock_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        # 常見格式：可能只有 PID，或含 host 資訊；用最保守的方式從字串裡抓一個整數
        for token in content.replace("\n", " ").split():
            try:
                pid = int(token)
                if pid > 0:
                    return pid
            except ValueError:
                continue
    except Exception:
        pass
    return None


def _is_file_older_than(lock_path: str, minutes: int) -> bool:
    try:
        mtime = os.path.getmtime(lock_path)
        return (time.time() - mtime) > (minutes * 60)
    except Exception:
        return False


def cleanup_stale_locks(log_dir: str, stale_minutes: int = 30, verbose: bool = True):
    """
    啟動前的保險：清理 log 目錄下疑似殘留的 .lock 檔。
    規則：
      1) 解析出 PID 且 psutil.pid_exists(pid) 為 False -> 刪除
      2) 無法解析 PID 且檔案過舊(> stale_minutes) -> 刪除
    """
    pattern = os.path.join(log_dir, "*.lock")
    for lock_path in glob.glob(pattern):
        try:
            pid = _read_pid_from_lock(lock_path)
            remove = False
            reason = ""
            if pid is not None:
                if not psutil.pid_exists(pid):
                    remove = True
                    reason = f"PID {pid} 不存在"
            else:
                if _is_file_older_than(lock_path, stale_minutes):
                    remove = True
                    reason = f"無 PID 且超過 {stale_minutes} 分鐘"

            if remove:
                os.remove(lock_path)
                if verbose:
                    print(f"[log] 清除殘留 lock：{lock_path}（原因：{reason}）")
        except Exception as e:
            if verbose:
                print(f"[log] 嘗試清除 lock 失敗：{lock_path}，{e}")


def _install_signal_safe_shutdown(verbose: bool = False):
    """註冊 atexit 與訊號處理，確保非正常結束時也能釋放 log 資源。"""
    atexit.register(logging.shutdown)

    def _handler(signum, frame):
        if verbose:
            print(f"[log] 收到訊號 {signum}，正在安全關閉 logging ...")
        try:
            logging.shutdown()
        finally:
            # 讓預設行為繼續（若你想直接結束程式，可在此 os._exit(1)）
            pass

    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGABRT):
        try:
            signal.signal(sig, _handler)
        except Exception:
            # 某些環境（例如執行緒或特定平臺）可能無法設定訊號
            pass


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


def get_logger(
    log_file_name='main_log',
    log_sub_dir="",
    DEBUG_flag=False,
    set_level="debug",
    hide_threadname_flag=False,
    hide_filename_flag=False,
    hide_funcname_flag=False,
    *,
    force_unlock_if_stale: bool = True,   # 新增：啟動時清 lock
    stale_minutes: int = 30,              # 新增：判定 lock 過舊的門檻
    verbose_lock_cleanup: bool = False    # 新增：是否印出清理訊息
):
    """ Creates a Log File and returns Logger object """

    windows_log_dir = './logs_dir/'
    linux_log_dir = './logs_dir/'

    # Build Log file directory, based on the OS and supplied input
    log_dir = windows_log_dir if os.name == 'nt' else linux_log_dir
    log_dir = os.path.join(log_dir, log_sub_dir)

    # Create Log file directory if not exists
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    # 啟動前嘗試清理殘留 lock
    if force_unlock_if_stale:
        cleanup_stale_locks(log_dir, stale_minutes=stale_minutes, verbose=verbose_lock_cleanup)

    # Build Log File Full Path
    logPath = log_file_name if os.path.exists(log_file_name) else os.path.join(log_dir, (str(log_file_name) + '.log'))

    # Create logger object and set the format for logging and other attributes
    logger = logging.Logger(log_file_name)
    logging.setLogRecordFactory(system_info_factory)

    level_dict = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "critical": logging.CRITICAL,
    }
    logger.setLevel(level_dict.get(set_level, logging.DEBUG))

    # 使用 ConcurrentRotatingFileHandler
    handler = ConcurrentRotatingFileHandler(
        logPath,
        maxBytes=50 * 1024 * 1024,
        backupCount=2,
        encoding="utf-8",
    )

    # 你的原本 formatter 規則維持
    log_str = '%(asctime)s $ %(levelname)-10s $ %(mem_percent).1f'
    if not hide_threadname_flag: log_str += ' $%(threadName)s'
    if not hide_filename_flag: log_str += ' $%(filename)s'
    if not hide_funcname_flag: log_str += ' $%(funcName)s'
    log_str += ' $ %(message)s'

    format_ = handler.setFormatter(CustomFormatter(log_str))
    logger.addHandler(handler)

    formatter = logging.Formatter(format_)

    if DEBUG_flag:
        streamHandler = logging.StreamHandler()
        streamHandler.setFormatter(formatter)
        logger.addHandler(streamHandler)

    # 註冊安全關閉（避免再次殘留 lock）
    _install_signal_safe_shutdown(verbose=verbose_lock_cleanup)

    return logger