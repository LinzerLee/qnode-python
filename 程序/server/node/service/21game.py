#-*- coding:utf-8 –*-
'''
Created on 2017年12月28日

@author: linzer
'''

from functools import partial
from net import Timestamp
from framework import Context, Service, Mail
import random, re

service_instance = None

rooms = {
    # roomname --> {
    #     users : {}
    #     anwser : {
    #        user1 : , 
    #        user2, user3},
    #     numbers : []
    # }
}

def cards(num1, num2, num3, num4):
    tmp1 = num1
    tmp2 = num2
    tmp3 = num3
    tmp4 = num4
    num1 = num1 % 10
    num2 = num2 % 10
    num3 = num3 % 10
    num4 = num4 % 10
    
    return u'''
              *****本期题目*****
.------.    .------.    .------.    .------.
|%d.--. |    |%d.--. |    |%d.--. |    |%d.--. |
| :/\: |    | :/\: |    | :/\: |    | :/\: |
| :\/: |    | :\/: |    | :\/: |    | :\/: |
| '--'%d|    | '--'%d|    | '--'%d|    | '--'%d|
`------'    `------'    `------'    `------'
   %2d          %2d          %2d          %2d
''' % (num1, num2, num3, num4, num1, num2, num3, num4, tmp1, tmp2, tmp3, tmp4)

def welcome(service, mail):
    result = u'''
***********************************************************
*   ██████╗  ██╗    ██████╗  █████╗ ███╗   ███╗███████╗   *
*   ╚════██╗███║   ██╔════╝ ██╔══██╗████╗ ████║██╔════╝   *
*    █████╔╝╚██║   ██║  ███╗███████║██╔████╔██║█████╗     *
*   ██╔═══╝  ██║   ██║   ██║██╔══██║██║╚██╔╝██║██╔══╝     *
*   ███████╗ ██║██╗╚██████╔╝██║  ██║██║ ╚═╝ ██║███████╗   *
*   ╚══════╝ ╚═╝╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═╝     ╚═╝╚══════╝   * 
***********************************************************
                  欢迎来到21.game游戏大厅                                                  
''' 
    service.send(mail.source(), errcode = 0, result = result)

def question():
    num1 = random.randint(1, 10)
    num2 = random.randint(1, 10)
    num3 = random.randint(1, 10)
    num4 = random.randint(1, 10)
    
    return (num1, num2, num3, num4, cards(num1, num2, num3, num4))

def waitTime():
    ts = Timestamp()
    sec = ts.minute() % 30 * 60 + ts.second()
    sec = 30 * 60 - sec
    m = sec / 60
    s = sec % 60
    
    return m, s

address2user = {}
userSession = {
    # user : {
    #     address
    #     room
    #}
}

def checkLogin(source):
    if source in address2user:
        return True
    else:
        return False

def checkInRoom(source):
    if checkLogin(source):
        user = address2user[source]
        if 'room' in userSession[user]:
            return True
        
    return False

def removeUserInfo(service, mail):
    addr = mail.dest()
    if addr in address2user:
        user = address2user[addr]
        del address2user[addr]
        del userSession[user]['address']
    

def recordUserInfo(service, mail):
    if mail['result']:
        result = mail['result']
        if 'user' in result:
            user = result['user']
            if user not in userSession:
                userSession[user] = {}
            userSession[user]['address'] = mail.dest()
            address2user[mail.dest()] = user

def redirectLogin(service, mail):
    if 'LOGIN' == mail['CMD']:
        service.redirect(mail, 'login', handler = recordUserInfo)
    elif 'LOGOUT' == mail['CMD']:
        service.redirect(mail, 'login', handler = removeUserInfo)
    else:
        service.redirect(mail, 'login')

def sys2User(recver, msg):
    if recver in userSession:
        addr = userSession[recver]['address']
        service_instance.send(addr, errcode = 0, result = msg)

def sys2Room(rname, msg):
    if rname in rooms:
        for recver in rooms[rname]['users']:
            sys2User(recver, msg)
            
def sys2All(msg):
    for recver in userSession:
        sys2User(recver, msg)
            
def chat2User(user, recver, msg, cmd = 'UMSG'):
    if recver in userSession:
        addr = userSession[recver]['address']
        result = {
            'CMD' : cmd,
            'user' : user,
            'message' : msg,
        }
        service_instance.send(addr, errcode = 0, result = result)

def chat2Room(user, rname, msg):
    if rname in rooms:
        for recver in rooms[rname]['users']:
            chat2User(user, recver, msg, 'RMSG')

def chat2All(user, msg):
    for recver in userSession:
        chat2User(user, recver, msg, 'BMSG')
        
def sendChatMsg(service, mail):
    user = address2user[mail.source()]
    cmd = mail['CMD']
    msg = mail['message']
    if 'UCHAT' == cmd:
        recver = mail['user']
        chat2User(user, recver, msg)
    elif 'RCHAT' == cmd:
        if not checkInRoom(mail.source()):
            result = {
                'CMD' : 'RMSG',
                'error' : u'不能发起房间聊天，请先进入一个游戏房间',
            }
            service.send(mail.source(), errcode = 0, result = result)
        else:
            rname = userSession[user]['room']
            chat2Room(user, rname, msg)
    elif 'BCHAT' == cmd:
        chat2All(user, msg)
    
def gameroom(service, mail):
    source = mail.source()
    result = {
        'CMD' : 'ROOM_REP',
    }
    
    if mail['roomname']:
        rname = mail['roomname']
        if rname not in rooms:
            rooms[rname] = {
                'users' : {},
                'answer' : {},
                'numbers' : None
            }
        
        user = address2user[mail.source()]
        if user in userSession and 'room' in userSession[user]:
            oldrname = userSession[user]['room']
            del rooms[oldrname]['users'][user]
        
        sys2Room(rname, u'%s 进入了聊天室' % user)
        ts = Timestamp().unixTime()
        userSession[user]['room'] = rname    
        rooms[rname]['users'][user] = ts
        result['roomname'] = rname
        if rooms[rname]['numbers'] is None:
            ms = waitTime()
            result['question'] = u'**********距离题目揭晓还有 %d 分 %d 秒**********' % ms
        else:
            result['question'] = rooms[rname]['numbers'][4]
            
        service.send(source, errcode = 0, result = result) 
    else:
        result['rooms'] = rooms.keys()
        service.send(source, errcode = 0, result = result)
    
def lobby(service, mail):
    if mail.source() in address2user:
        user = address2user[mail.source()]
        if 'room' in userSession[user]:
            rname = userSession[user]['room']
            del userSession[user]['room']
            del rooms[rname]['users'][user]
        
    service.send(mail.source(), errcode = 0, result = '欢迎回到21.game游戏大厅')
 
def sendQ(service, mail):
    if not checkInRoom(mail.source()):
        service.send(mail.source(), errcode = 0, result = u'请先进入一个游戏房间')
        return
    
    user = address2user[mail.source()]
    rname = userSession[user]['room']
    ms = waitTime()
    if rooms[rname]['numbers'] is None:
        result = u'**********距离题目揭晓还有 %d 分 %d 秒**********' % ms
    else:
        result = rooms[rname]['numbers'][4]
        ms = (ms[0] - 10, ms[1])
        if 'owner' not in rooms[rname]:
            result += u'注意：请在20分钟内提交答案，20分钟以后将进行发榜，答题剩余时间 %d 分 %d 秒' % ms
        else:
            owner = rooms[rname]['owner']
            # (user, answer, value, ts)
            result += u'恭喜 %s 在 %s 提交了最佳答案 %s(%s), 获得了本期题目冠军' % (owner[0], owner[3].format(), owner[1], owner[2])
    service.send(mail.source(), errcode = 0, result = result)
 
def submitAnswer(service, mail):
    if not checkInRoom(mail.source()):
        service.send(mail.source(), errcode = 0, result = u'请先进入房间(ROOM)')
    else:    
        user = address2user[mail.source()]
        rname = userSession[user]['room']
        if rooms[rname]['numbers'] is None:
            ms = waitTime()
            result = u'**********距离题目揭晓还有 %d 分 %d 秒**********' % ms
        else:
            if 'owner' in rooms[rname]:
                owner = rooms[rname]['owner']
                # (user, answer, value, ts)
                result = u'%s 已经在 %s 提交了最佳答案 %s(%s), 获得了本期题目冠军' % (owner[0], owner[3].format(), owner[1], owner[2])
            elif user in rooms[rname]['answer']:
                answer = rooms[rname]['answer'][user][0]
                value = rooms[rname]['answer'][user][1]
                ts = rooms[rname]['answer'][user][2]
                result = u'您在 %s 已经提交过答案了, 之前的提交的答案是 %s(%d)' % (ts.format(), answer, value)
            else:
                quest = rooms[rname]['numbers']
                answer = mail['answer']
                answer = re.sub('\s','',answer)
                nums = re.split('\(|\)|\+|-|\*|/', answer)
                nums = filter(lambda p: len(p), nums)
                if 4 == len(nums) and nums == map(str, quest[:4]):
                    value = int(eval(answer))
                    ts = Timestamp()
                    rooms[rname]['answer'][user] = (answer, value, ts)
                    if value > 21:
                        result = u'答案提交成功, 您的计算结果是 %d(>21), 您失去了本次夺冠的机会' % value
                    else:
                        ms = waitTime()
                        if value == 21 and ms[0] == 29 and ms[1] >= 45:
                            sec = 60 - ms[1]
                            rooms[rname]['owner'] = (user, answer, value, ts)
                            result = u'OMG, %s 在 %d 秒内神速地给出了最佳答案 %s , 快收下我的膝盖吧∑(っ °Д °;)っ' % (user, sec, answer)
                            sys2Room(rname, result)
                            return
                        else:
                            result = u'答案提交成功, 您的计算结果是 %d, 请耐心等待揭榜' % value
                else:
                    result = u'提交的答案不合法'
        
        service.send(mail.source(), errcode = 0, result = result)
     
CMD = {                                 
    'WELCOME' : welcome,                
    'REG'     : redirectLogin,               
    'LOGIN'   : redirectLogin,   
    'LOGOUT'  : redirectLogin,
    'UCHAT'   : sendChatMsg, 
    'RCHAT'   : sendChatMsg,
    'BCHAT'   : sendChatMsg,
    'ROOM'    : gameroom,  
    'LOBBY'   : lobby, 
    'Q'       : sendQ,
    'A'       : submitAnswer 
}

def statistics():
    # 统计答案
    for rname in rooms:
        room = rooms[rname]
        if 'owner' not in room: 
            owner = None
            ownerValue = None
            ownerTs = None
            for user in room['answer']:
                answer = room['answer'][user][0]
                value = room['answer'][user][1]
                ts = room['answer'][user][2]
                if owner is None and value <= 21 or             \
                    value > ownerValue and value <= 21 or       \
                        value == ownerValue and ts.unixTime() < ownerTs.unixTime():
                    owner = user
                    ownerAnswer = answer
                    ownerTs = ts
                    ownerValue = value
                    
            if owner is not None:
                msg = u'恭喜 %s 获得本场冠军，提交的答案是 %s' % (owner, ownerAnswer)
                sys2Room(rname, msg)
        
        rooms[rname] = {
            'users' : {},
            'answer' : {},
            'numbers' : None
        }
        
    ms = waitTime()
    service_instance.timerAfter(publish, ms[0] * 60 + ms[1])
        
        
def publish():
    # 发布新的题目
    for rname in rooms:
        rooms[rname]['numbers'] = question()
        sys2Room(rname, rooms[rname]['numbers'][4])
        
    ms = waitTime()
    ms = (ms[0] - 10, ms[1])
    service_instance.timerAfter(statistics, ms[0] * 60 + ms[1])
    
def init(service):
    global service_instance
    service_instance = service
    service.send('log', log = '21game service is initializing')
    service.listen(8000, 'json')
    ms = waitTime()
    service.timerAfter(publish, ms[0] * 60 + ms[1])
    
def dispatch(service, mail):
    if mail.isOneWay():
        cmd = mail['CMD']
        if not checkLogin(mail.source()) and cmd not in ('LOGIN', 'REG', 'WELCOME'):
            service.send(mail.source(), errcode = 0, result = u'请先登录(LOGIN), 如果没有账户请注册(REG), 如果有疑问请查询帮助(HELP)')
            return
        
        if cmd in CMD:
            CMD[cmd](service, mail)
        else:
            service.send(mail.source(), errcode = 1, result = u'服务器不支持命令 %s' % cmd)
        
def release(service):
    service.send('log', log = '21game service is releasing')