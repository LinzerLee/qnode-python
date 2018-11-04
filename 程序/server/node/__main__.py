#-*- coding:utf-8 –*-
'''
Created on 2017年12月24日

@author: linzer
'''
import threading, sys, time
from framework import Context, Gate
from net import Timestamp

if __name__ == '__main__':
    # 1. 创建服务框架上下文
    ctx = Context()
    # 2. 启动网关服务
    gate = Gate(ctx)
    threading.Thread(target = gate).start()
    # 3. 启动基础服务
    # ctx.register(Service('XXX'))
    # 4. 加载配置文件
    config = './node/config/standalone.cfg'
    if len(sys.argv) > 1:
        config = sys.argv[1]
    ctx.loadConfig(config)
    # Main Loop
    try:
        while ctx.isRunning():
            # 5. 邮件分发
            ctx.dispatchMail()
            # 6. 处理运行队列
            ctx.runTaskQueue()
			# 7. CPU让出控制权
            time.sleep(0)
    except KeyboardInterrupt:
        ctx.close()
    finally:
        gate.stop()
        ctx.exit()