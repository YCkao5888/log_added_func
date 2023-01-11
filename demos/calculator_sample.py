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
