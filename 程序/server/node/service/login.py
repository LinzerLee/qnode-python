#-*- coding:utf-8 –*-
'''
Created on 2017年12月28日

@author: linzer
'''

from functools import partial
from net import Timestamp
from framework import Context, Service, Mail

online = {
    # user : { session }
}

def register(service, mail):
    def getUserInfo(service, mail):
        if mail['result'] is None:
            session = Timestamp().unixTime()
            service.send('cache', CMD = 'SET', key = 'user.' + user, value = session)
            service.send('cache', CMD = 'SET', key = 'user.' + user + '.online', value = 0)
            service.send('cache', CMD = 'SET', key = 'user.' + user + '.password', value = password)
            service.response(source, mailSession, errcode = 0, result = u'注册成功')
        else:
            service.response(source, mailSession, errcode = 0, result = u'用户已存在')
    
    source = mail.source()
    # 验证登陆命令语法
    if not mail['user'] or not mail['password']:
        service.send(source, errcode = 1, result = 'REG command syntax error')
        return
    
    mailSession = mail.session()
    user = mail['user']
    password = mail['password'] 
    service.request('cache', callback = getUserInfo, CMD = 'GET', key = 'user.' + user)

def login(service, mail):
    def checkPassword(last, service, mail):
        session = Timestamp().unixTime()
        if password == mail['result']:
            if user not in online:
                online[user] = {
                    'session' : session
                }
                
            service.send('cache', CMD = 'SET', key = 'user.' + user, value = session)
            result = {                          
                'CMD' : 'LOGIN_REP',                
                'user' : user,             
                'session' : session,
                'last' : last          
            }
            service.response(source, mailSession, errcode = 0, result = result)
        else:
            result = {
                'CMD' : 'LOGIN_REP',
                'error' : u'密码错误'
            }
            
            service.response(source, mailSession, errcode = 0, result = result)
    
    def checkUserExist(service, mail):
        if mail['result'] is None:
            result = {
                'CMD' : 'LOGIN_REP',
                'error' : u'用户不存在'
            }
            service.response(source, mailSession, errcode = 0, result = result)
        else:
            last = mail['result']
            callback = partial(checkPassword, last)
            key = 'user.' + user + '.password'
            service.request('cache', callback = callback, CMD = 'GET', key = key)
    
    source = mail.source()
    mailSession = mail.session()
    # 验证登陆命令语法
    if not mail['user'] or not mail['password']:
        service.response(source, mailSession, errcode = 1, result = 'REG command syntax error')
        return
    
    user = mail['user']
    password = mail['password']
    service.request('cache', callback = checkUserExist, CMD = 'GET', key = 'user.' + user)
        
 
def logout(service, mail):
    def updateOnlineTime(service, mail):
        onlineTime = mail['result']
        onlineTime += time
        service.send('cache', CMD = 'SET', key = key, value = onlineTime)
        onlineTime = onlineTime / 1000000.0
        service.response(source, mailSession, errcode = 0, result = u'下线成功，累计在线时长 %f 秒' % onlineTime)
    
    source = mail.source()
    mailSession = mail.session()
    user = mail['user']
    session = mail['session']
    if user in online:
        time = (Timestamp().unixTime() - session)
        key = 'user.' + user + '.online'
        service.request('cache', callback = updateOnlineTime, CMD = 'GET', key = key)
    else:
        service.response(source, mailSession, errcode = 1, result = u'请登录21.game游戏大厅')
          
CMD = {                                 
    'REG'     : register,               
    'LOGIN'   : login,
    'LOGOUT'  : logout,                  
}

def init(service):
    print Timestamp.now().format(), 'login service is initializing'
    
def dispatch(service, mail):
    cmd = mail['CMD']
    if cmd in CMD:
        CMD[cmd](service, mail)
    else:
        if mail.isOneWay():
            service.send(mail.source(), errcode = 1, result = u'无效命令 %s' % cmd)
        else:
            service.response(mail.source(), mail.session(), result = u'无效命令 %s' % cmd)
        
def release(service):
    print Timestamp.now().format(), 'login service is releasing'