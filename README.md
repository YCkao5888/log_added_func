# log_added_func
* 可以在程式碼中間插入想要的log，或者直接把裝飾器放在函數前，其會自動記錄其輸入和輸出資訊。

## Getting Started
* 輸出的log會自動存取其log時間、file_name、func_name。 
* 輸出內容：
```
%(asctime)s $ %(levelname)-10s $(mem_percent) $%(threadName)s $ %(filename)s $ %(funcName)s $ %(message)s
```
* 客製化log：在想要的地方下Log，可以設定等級。 
* 通用型log：用裝飾器包裝，可以將該func運行error列印出來，也會列印輸入的參數和輸出的值。
* log的存放位置：當前執行的檔案目錄
   > ./logs_dir/ 

  
# Installing：
pip install log_added_func-X.X.X-py3-none-any.whl
* 相依套件
  * concurrent-log-handler
  * psutil
  * pywin32 (If you are using Mac or Linux, ignore this key point.)

# Examples
範例1:class內有錯誤raise的log
```python
from log_added_func import log
from log_added_func import log_decorator

class Calculator():
    def __init__(self, first=0, second=0):
        self.first = first
        self.second = second

        # Initializing logger object to write custom logs
        self.logger_obj = log.get_logger()

    # let self.logger_obj remove from __dict__, it will not pickle.
    def __getstate__(self):
        d = dict(self.__dict__)
        del d['logger_obj']
        return d

    def __setstate__(self, d):
        self.__dict__.update(d)  # I *think* this is a safe way to do it

    @log_decorator.log_decorator()
    def add(self, third=0, fourth=0):
        # writing custom logs specific to function, outside of log decorator, if needed
        self.logger_obj.critical("Add function custom log, outside decorator")
        self.logger_obj.error("Add function custom log, outside decorator")
        self.logger_obj.warning("Add function custom log, outside decorator")
        self.logger_obj.info("Add function custom log, outside decorator")
        self.logger_obj.debug("Add function custom log, outside decorator")

        try:
            return self.first + self.second + third + fourth
        except:
            raise

    @log_decorator.log_decorator()
    def divide(self):
        self.logger_obj.info("Divide function custom log, outside decorator")
        try:
            return self.first / self.second
        except:
            raise
        
        
if __name__ == '__main__':
    calculator = Calculator(5, 0)
    calculator.add(third=2,fourth=3)
    calculator.divide()
```
範例2: 多進程放log
```python
import multiprocessing as mp
from log_added_func import log
from log_added_func import log_decorator

def task(num):
    logger_obj = log.get_logger(log_file_name='test_log')
    print('This is Process: ', num)
    logger_obj.info(f"This is Process: {num}")


if __name__=='__main__':
    num_process = 5
    process_list = []
    for i in range(num_process):
        process_list.append(mp.Process(target=task, args=(i,)))
        process_list[i].start()

    for i in range(num_process):
        process_list[i].join()
```
## 客製化log
1. 載入：
```python
from log_added_func import log
from log_added_func import log_decorator
```
3. 初始化：
```python
logger_obj = log.get_logger()
```
4. 在想要的地方放log： 
```python
logger_obj.info("Add function custom log, outside decorator")
```
5. log輸出範例：
    >2023-01-11 10:13:48,856 $ DEBUG      $ 59.6 $MainThread $ calculator_sample.py $ add $ Add function custom log, outside decorator
6. 設定等級：
    - 可以設定critical、error、warning、info、debug
    - 範例：logger_obj.warning("Add function custom log, outside decorator")
   
## 通用型log
1. 載入：
```python
from log_added_func import log
from log_added_func import log_decorator
```
2. 在想要的method放:
```python
@log_decorator.log_decorator()
def smaple():
    pass
```
3. log輸出範例:
    > 2022-11-09 16:23:58,791 - INFO       - calculator.py - divide - Arguments:  - Begin function \
    2022-11-09 16:23:58,792 - ERROR      - calculator.py - divide - Exception: division by zero


## 其他說明
1. 可以設定log單檔儲存的大小
    - 1 * 1024 * 1024 = 1MB
    - ConcurrentRotatingFileHandler(logPath, maxBytes=50 * 1024 * 1024, backupCount=2)  
3. log存放的位置
    - window: c:\\logs_dir\\
    - linux: ./logs_dir/ # 當前目錄
    - 若要修改可以在log.py的get_logger調整
4. log檔案名稱
    - 預設:main_log
    - 客製化:在初始化時設定get_logger(log_file_name=<font color=red>"sample_name_log"</font>)
    - 通用型:@log_decorator.log_decorator(log_file_name=<font color=red>"sample_name_log"</font>)
5. log已資料夾存放
    - 預設:無資料夾
    - 若要依資料夾分類log也可以對get_logger下參數log_sub_dir

## TODO
- 目前不會show實例化的class名稱

## other
- pickle包裝logger會有問題 # 在calculator.py有解決範例
    - https://stackoverflow.com/questions/2999638/how-to-stop-attributes-from-being-pickled-in-python
- 多進程會有logging同時讀寫問題: # 理論上已經透過ConcurrentRotatingFileHandler解決
    - https://www.qnjslm.com/ITHelp/996.html
    - https://stackoverflow.com/questions/22459850/permissionerror-when-using-python-3-3-4-and-rotatingfilehandler
    - https://blog.gdyshi.top/2018/06/27/logging_multiprocess/
    - https://www.programmersought.com/article/43941158027/