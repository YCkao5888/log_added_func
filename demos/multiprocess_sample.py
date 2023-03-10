import multiprocessing as mp
from log_added_func import log
from log_added_func import log_decorator

@log_decorator.log_decorator()
def task(num):
    logger_obj = log.get_logger(log_file_name='test_log')
    # print('This is Process: ', num)
    logger_obj.info(f"This is Process: {num}")


if __name__=='__main__':
    num_process = 5
    process_list = []
    for i in range(num_process):
        process_list.append(mp.Process(target=task, args=(i,)))
        process_list[i].start()

    for i in range(num_process):
        process_list[i].join()