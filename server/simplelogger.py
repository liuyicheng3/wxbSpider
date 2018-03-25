# coding=utf-8
import logging

# 不能设置basicConfig  这回导致打印两遍
# logging.basicConfig(level=logging.NOTSET)
# 创建一个logger
logger = logging.getLogger()
logger.setLevel(logging.NOTSET)

# 创建一个handler，用于写入日志文件
fh = logging.FileHandler('wxb.log')

# 再创建一个handler，用于输出到控制台
ch = logging.StreamHandler()

# 定义handler的输出格式formatter
formatter = logging.Formatter('%(asctime)s [%(filename)s:%(lineno)s][%(levelname)s] %(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)

# 定义一个filter
# filter = logging.Filter('mylogger.child1.child2')
# fh.addFilter(filter)

# 给logger添加handler
#logger.addFilter(filter)
logger.addHandler(fh)
logger.addHandler(ch)

