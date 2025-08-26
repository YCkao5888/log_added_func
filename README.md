# log_added_func 

Python logging 小套件：
- 以 `ConcurrentRotatingFileHandler` 避免多進程同時寫檔衝突。
- 啟動前**自動清理殘留 `.lock`**（崩潰/非正常結束後的卡死保險）。
- 支援**依檔案大小輪替**與**依最後修改時間覆蓋**（清空重寫），並可設定**觸發優先度**。
- 註冊 `atexit` 與 `SIGINT/SIGTERM/SIGABRT` 安全關閉，減少殘留鎖。
- 內建裝飾器，快速記錄函式**參數/回傳值**與**例外**。

---

## 特色 (Features)
- **多進程安全輪替**：使用 `ConcurrentRotatingFileHandler`。
- **殘鎖清理**：啟動前掃描 `logs_dir` 的 `*.lock`，PID 不存在或檔案過舊即移除。
- **大小輪替（可關）**：`enable_size_rotation`、`size_max_bytes`、`size_backup_count`。
- **時間覆蓋（可關）**：`enable_time_overwrite`、`time_overwrite_minutes`、`time_overwrite_mode="truncate"`。
- **優先度**：`rotation_priority` = `"size_first"` / `"time_first"`。
- **彈性輸出格式**：可隱藏 `threadName`/`filename`/`funcName` 欄位。
- **Console 同步輸出**：`DEBUG_flag=True` 時加掛 `StreamHandler`。
- **裝飾器**：`@log_decorator.log_decorator(...)` 自動記錄入參/出參，捕捉例外並以 `ERROR` 紀錄。

---

## 安裝 (Installation)
```bash
pip install log-added-func
```
相依套件：
- `concurrent-log-handler`
- `psutil`
- `pywin32`（僅 Windows 需要；macOS/Linux 可忽略）

---

## 快速開始 (Quickstart)
```python
from log_added_func import log

logger = log.get_logger()
logger.info("服務啟動完成")
```
- 預設輸出目錄：`./logs_dir/`（相對於**程式啟動時的工作目錄**）。
- 預設檔名：`main_log.log`。
- 預設大小輪替：50MB、保留 2 個備份（`.1`, `.2`）。

> Log 格式（預設）：
>
> `%(asctime)s $ %(levelname)-10s $ %(mem_percent).1f $%(threadName)s $ %(filename)s $ %(funcName)s $ %(message)s`

---

## API — `get_logger(...)`
**簽名**（節錄重點參數）：
```python
get_logger(
    log_file_name='main_log',
    log_sub_dir='',
    DEBUG_flag=False,
    set_level='debug',
    hide_threadname_flag=False,
    hide_filename_flag=False,
    hide_funcname_flag=False,
    *,
    # Lock 殘留保險
    force_unlock_if_stale=True,
    stale_minutes=30,
    verbose_lock_cleanup=False,
    # 大小輪替
    enable_size_rotation=True,
    size_max_bytes=50*1024*1024,
    size_backup_count=2,
    # 時間覆蓋
    enable_time_overwrite=False,
    time_overwrite_minutes=30*1440,
    time_overwrite_mode='truncate',
    # 觸發優先度
    rotation_priority='size_first',  # 或 'time_first'
)
```

### 參數說明
| 參數 | 型別/範例 | 預設 | 說明 |
|---|---|---|---|
| `log_file_name` | `"main_log"` | `main_log` | 日誌檔名（不需副檔名，實際為 `*.log`）。|
| `log_sub_dir` | `"serviceA"` | `""` | 子目錄（會建立在 `./logs_dir/` 之下）。|
| `DEBUG_flag` | `True/False` | `False` | 啟用時同步輸出到終端機（`StreamHandler`）。|
| `set_level` | `"debug"/"info"/...` | `"debug"` | Logger 等級（會影響寫入哪些等級）。|
| `hide_threadname_flag` | `True/False` | `False` | 隱藏 `threadName` 欄位。|
| `hide_filename_flag` | `True/False` | `False` | 隱藏 `filename` 欄位。|
| `hide_funcname_flag` | `True/False` | `False` | 隱藏 `funcName` 欄位。|
| `force_unlock_if_stale` | `True/False` | `True` | 啟動前清理殘留 `.lock`。|
| `stale_minutes` | `int`（例：30） | `30` | 殘鎖過舊判定（分鐘）。|
| `verbose_lock_cleanup` | `True/False` | `False` | 印出殘鎖清理細節（除錯用）。|
| `enable_size_rotation` | `True/False` | `True` | 是否啟用**大小輪替**。|
| `size_max_bytes` | `int`（例：`50*1024*1024`） | `50MB` | 單檔上限，達上限即輪替。|
| `size_backup_count` | `int`（例：2） | `2` | 輪替保留份數（`.1` 到 `.N`）。|
| `enable_time_overwrite` | `True/False` | `False` | 是否啟用**時間覆蓋**（清空重寫）。|
| `time_overwrite_minutes` | `int`（例：1440） | `0` | 若檔案最後修改時間距今超過此分鐘數 → 覆蓋。|
| `time_overwrite_mode` | `'truncate'` | `'truncate'` | 覆蓋策略，目前支援清空現檔（保留檔名）。|
| `rotation_priority` | `'size_first'/'time_first'` | `'size_first'` | 啟動檢查時，大小與時間觸發條件的處理優先順序。|

> **優先度行為**（啟動檢查階段）：
> - `time_first`：若「時間覆蓋」觸發 → 先清空檔案；否則再看是否「大小輪替」。
> - `size_first`：若「大小輪替」觸發 → 先輪替檔案；否則再看是否「時間覆蓋」。

---

## API — 裝飾器 `@log_decorator.log_decorator(...)`
- 作用：自動記錄函式**開始**、**參數**、**回傳**與**例外**。
- 成功結束 → `INFO`；發生例外 → `ERROR`（例外會被重新拋出）。
- 可傳入與 `get_logger` 相同的常用參數（如 `log_file_name`、`log_sub_dir`、`DEBUG_flag`、`set_level`）。

**範例**：
```python
from log_added_func import log, log_decorator

class Calculator:
    def __init__(self, first=0, second=0):
        self.first = first
        self.second = second
        self.logger_obj = log.get_logger()

    # 讓 logger 不被 pickle
    def __getstate__(self):
        d = dict(self.__dict__)
        d.pop('logger_obj', None)
        return d

    def __setstate__(self, d):
        self.__dict__.update(d)

    @log_decorator.log_decorator()
    def add(self, third=0, fourth=0):
        self.logger_obj.info("Add function custom log, outside decorator")
        return self.first + self.second + third + fourth

    @log_decorator.log_decorator()
    def divide(self):
        self.logger_obj.info("Divide function custom log, outside decorator")
        return self.first / self.second
```

---

## 檔案命名與存放位置
- 預設目錄：`./logs_dir/`（**相對於當前工作目錄**），可用 `log_sub_dir` 分類：
  - 例：`get_logger(log_sub_dir="serviceA")` → `./logs_dir/serviceA/`。
- 預設檔名：`main_log.log`；可用 `log_file_name` 自訂。
- 若需集中式路徑（避免不同工作目錄分散），建議：
  - 在專案內建立統一的 `config/log.py` 供所有模組呼叫。
  - 或以環境變數指定根目錄後在 `get_logger` 內讀取。

> 權限提醒：不同帳號可能導致檔案/資料夾權限不一致；請確保執行帳號對 `logs_dir` 具有建立/刪除/寫入權限。

---

## 輪替/覆蓋策略 — 實務補充
- **大小輪替**：超過 `size_max_bytes` → 以 `.1`, `.2`… 方式滾動備份，保留 `size_backup_count` 份。
- **時間覆蓋**：若「最後修改時間距今 > `time_overwrite_minutes`」→ 直接清空現檔（`truncate`），檔名不變。
- **兩者同時啟用**：由 `rotation_priority` 決定先做哪一個（啟動當下的單次檢查）。
- **執行中**：大小輪替由 `ConcurrentRotatingFileHandler` 自行處理；時間覆蓋目前僅在**啟動前檢查**階段生效（避免執行中主動清空造成併發衝突）。

---

## 多進程/容器化建議
- 同一台機器上的多進程可共用同一路徑與檔名；`ConcurrentRotatingFileHandler` 會處理鎖定。
- 容器（Docker/K8s）建議將 `logs_dir` 掛載到持久化卷（volume），以避免容器重建時遺失。
- 大量寫入時，建議降低 `set_level` 或拆分服務各自 `log_sub_dir`。

---

## 疑難排解 (Troubleshooting)
- **卡在 lock**：啟動前已自動清理；仍卡住時可開 `verbose_lock_cleanup=True` 觀察清理訊息，或手動刪除 `*.lock`。若 lock 由高權限建立，低權限帳號可能無法刪除。
- **PermissionError**：確認 `logs_dir` 可寫入/刪除；Windows 可能需以系統管理員權限執行或調整資料夾 ACL。
- **檔案不在預期位置**：請確認**工作目錄**與 `log_sub_dir` 設定；若以 IDE/排程器啟動，工作目錄可能不同。
- **輪替後找不到舊檔**：檢查 `size_backup_count` 設定；超過上限的最舊檔會被移除。

---

## 範例集 (Examples)

### 1) 預設設定（大小輪替 ON）
```python
logger = log.get_logger()
```

### 2) 只用時間覆蓋（例如每日清空），時間優先
```python
logger = log.get_logger(
    enable_size_rotation=False,
    enable_time_overwrite=True,
    time_overwrite_minutes=1440,  # 1 天
    rotation_priority='time_first',
)
```

### 3) 大小輪替 + 時間覆蓋並存，大小優先
```python
logger = log.get_logger(
    enable_size_rotation=True,
    size_max_bytes=100*1024*1024,
    size_backup_count=5,
    enable_time_overwrite=True,
    time_overwrite_minutes=720,  # 12 小時
    rotation_priority='size_first',
)
```

### 4) 多進程寫同一檔
```python
import multiprocessing as mp
from log_added_func import log, log_decorator

@log_decorator.log_decorator()
def task(num):
    logger = log.get_logger(log_file_name='test_log')
    logger.info(f"This is Process: {num}")

if __name__ == '__main__':
    ps = [mp.Process(target=task, args=(i,)) for i in range(5)]
    [p.start() for p in ps]
    [p.join() for p in ps]
```

---

## 變更紀錄 (Changelog)
- **2025-08-26**
  - 新增：依「最後修改時間」判斷的**時間覆蓋**（`enable_time_overwrite`、`time_overwrite_minutes`、`time_overwrite_mode`）。
  - 新增：**優先度**（`rotation_priority` = `size_first`/`time_first`）。
  - 新增：`enable_size_rotation` 可關閉大小輪替；保留 `size_max_bytes`、`size_backup_count` 可調。
  - 強化：啟動前依優先度先做單次檢查（必要時手動輪替或清空），再建立 handler。
  - 強化：`atexit` + 訊號處理，減少殘留鎖；殘鎖清理訊息可切換 `verbose_lock_cleanup`。

---


