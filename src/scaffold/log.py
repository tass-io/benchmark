import logging

logger = logging.Logger

def init():
    logger = logging.getLogger('tass-benchmark')
    # 关于日志的书写只要有四个步骤：
    # （1）Loggers: 创建
    # （2）Handlers:把日志传送给合适的目标
    # （3）Filters: 过滤出想要的内容
    # （4）Formatters: 格式化

    # 日志等级（从小到大）：
    # debug()-->info()-->warning()-->error()-->critical()

    # Step 1: Loggers, 并设置全局level
    logger.setLevel(logging.DEBUG)

    # Step 2: Handler
    # print to screen
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    # write to file
    fh = logging.FileHandler('tass-benchmark.log')
    fh.setLevel(logging.WARNING)

    # Step 3: Formatter
    my_formatter = logging.Formatter('[%(asctime)s][%(pathname)s][%(funcName)s][line %(lineno)d][%(levelname)s] %(message)s')
    ch.setFormatter(my_formatter)
    fh.setFormatter(my_formatter)

    logger.addHandler(ch)
    logger.addHandler(fh)

    # log.debug('This is a debug log.')
    # log.info('This is a info log.')
    # log.warning('This is a warning log.')
    # log.error('This is a error log.')
    # log.critical('This is a critial log.')

    return logger

def oki():
    logger.info('happy')
def doki():
    logger.debug('hao ba')