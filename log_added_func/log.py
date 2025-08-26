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
from typing import Literal


def _read_pid_from_lock(lock_path: str) -> int | None:
    """嘗試從 lock 檔讀取 PID；若無法解析則回傳 None。"""
    try:
        with open(lock_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
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


def _is_file_older_than(path: str, minutes: int) -> bool:
    try:
        mtime = os.path.getmtime(path)
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
            pass

    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGABRT):
        try:
            signal.signal(sig, _handler)
        except Exception:
            pass


class CustomFormatter(logging.Formatter):
    """ Custom Formatter:
    1) Overrides 'funcName' with 'func_name_override'
    2) Overrides 'filename' with 'file_name_override'
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
    record.mem_percent = mem.percent
    return record


def _manual_size_rollover(base_path: str, backup_count: int):
    """
    在建立 handler 之前，手動進行最簡化的 .1, .2 ... 輪替。
    僅在單機啟動前使用，避免與其他程序搶同一檔案。
    """
    if backup_count <= 0:
        return
    # 刪除最舊
    oldest = f"{base_path}.{backup_count}"
    if os.path.exists(oldest):
        try:
            os.remove(oldest)
        except Exception:
            pass
    # 依序後移
    for i in range(backup_count - 1, 0, -1):
        src = f"{base_path}.{i}"
        dst = f"{base_path}.{i+1}"
        if os.path.exists(src):
            try:
                os.replace(src, dst)  # 原子性較佳（Windows/Unix表現視檔案系統）
            except Exception:
                pass
    # 目前檔案變成 .1
    if os.path.exists(base_path):
        try:
            os.replace(base_path, f"{base_path}.1")
        except Exception:
            pass


def get_logger(
    log_file_name='main_log',
    log_sub_dir="",
    DEBUG_flag=False,
    set_level="debug",
    hide_threadname_flag=False,
    hide_filename_flag=False,
    hide_funcname_flag=False,
    *,
    # --- Lock殘留保險 ---
    force_unlock_if_stale: bool = True,
    stale_minutes: int = 30,
    verbose_lock_cleanup: bool = False,
    # --- 檔案大小（可關閉/調參） ---
    enable_size_rotation: bool = True,
    size_max_bytes: int = 50 * 1024 * 1024,
    size_backup_count: int = 4,
    # --- 依「最後修改時間」覆蓋（可關閉/調參） ---
    enable_time_overwrite: bool = False,
    time_overwrite_minutes: int = 30 * 1440 ,  # 幾分鐘未更新就覆蓋；0 表示不啟用（或請搭配 enable_time_overwrite=False）; 1440(一天)
    time_overwrite_mode: Literal["truncate"] = "truncate",
    # --- 觸發優先度 ---
    rotation_priority: Literal["size_first", "time_first"] = "size_first",
):
    """建立並回傳 Logger 物件，具備：
       1) 殘留 .lock 清理
       2) 檔案大小（可關/可調）
       3) 依最後修改時間覆蓋（可關/可調）
       4) 兩者優先度設定（size_first / time_first）
    """
    windows_log_dir = './logs_dir/'
    linux_log_dir = './logs_dir/'

    # 目錄
    log_dir = windows_log_dir if os.name == 'nt' else linux_log_dir
    log_dir = os.path.join(log_dir, log_sub_dir)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    # 啟動前：清理殘留 lock
    if force_unlock_if_stale:
        cleanup_stale_locks(log_dir, stale_minutes=stale_minutes, verbose=verbose_lock_cleanup)

    # 檔案路徑
    logPath = log_file_name if os.path.exists(log_file_name) else os.path.join(log_dir, (str(log_file_name) + '.log'))

    # --- 啟動檢查（依優先度先處理一次） ---
    file_exists = os.path.exists(logPath)
    size_trigger = False
    time_trigger = False

    if file_exists:
        try:
            if enable_size_rotation and size_max_bytes and size_max_bytes > 0:
                size_trigger = os.path.getsize(logPath) >= size_max_bytes
        except Exception:
            size_trigger = False
        try:
            if enable_time_overwrite and time_overwrite_minutes and time_overwrite_minutes > 0:
                time_trigger = _is_file_older_than(logPath, time_overwrite_minutes)
        except Exception:
            time_trigger = False

        # 依優先度處理
        if rotation_priority == "time_first":
            if time_trigger:
                # 覆蓋（清空）舊檔
                if time_overwrite_mode == "truncate":
                    try:
                        open(logPath, "w", encoding="utf-8").close()
                        # 清空後，大小觸發自然解除
                        size_trigger = False
                    except Exception:
                        pass
            elif size_trigger:
                _manual_size_rollover(logPath, size_backup_count)
        else:  # size_first
            if size_trigger:
                _manual_size_rollover(logPath, size_backup_count)
                # 輪替後，新的現行檔會由 handler 打開，時間觸發失效
                time_trigger = False
            elif time_trigger:
                if time_overwrite_mode == "truncate":
                    try:
                        open(logPath, "w", encoding="utf-8").close()
                    except Exception:
                        pass

    # --- 建立 logger / handler ---
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

    # 依開關決定 maxBytes；0 表示停用
    max_bytes = size_max_bytes if enable_size_rotation and size_max_bytes > 0 else 0

    handler = ConcurrentRotatingFileHandler(
        logPath,
        maxBytes=max_bytes,
        backupCount=size_backup_count,
        encoding="utf-8",
    )

    # 格式
    log_str = '%(asctime)s $ %(levelname)-10s $ %(mem_percent).1f'
    if not hide_threadname_flag: log_str += ' $%(threadName)s'
    if not hide_filename_flag: log_str += ' $%(filename)s'
    if not hide_funcname_flag: log_str += ' $%(funcName)s'
    log_str += ' $ %(message)s'

    formatter_obj = CustomFormatter(log_str)
    handler.setFormatter(formatter_obj)
    logger.addHandler(handler)

    if DEBUG_flag:
        streamHandler = logging.StreamHandler()
        streamHandler.setFormatter(formatter_obj)
        logger.addHandler(streamHandler)

    # 註冊安全關閉
    _install_signal_safe_shutdown(verbose=verbose_lock_cleanup)

    return logger
