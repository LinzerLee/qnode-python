#-*- coding:utf-8 –*-
'''
Created on 2018年03月12日

@author: linzer
'''

from functools import partial
from net import Timestamp
from framework import Context, Service, Mail
import random, re
from uuid import UUID, uuid1

class Message(object): 
    def __init__(self, _type, _value):
        if not isinstance(_type, (str, unicode, UUID)):
            raise TypeError, 'type param is not str or UUID type'

        if isinstance(_type, (str, unicode)):
            self.type = UUID(_type)

        if isinstance(_value, UUID):
            self._value = str(_value)

        self.type = _type
        self.value = _value

    def Return(self):
        return {
            "Type" : str(self.type),
            "Value" : self.value
        }

    @staticmethod
    def MString(value):
        if not isinstance(value, (str, unicode)):
            raise TypeError, 'value param is not str or unicode type'

        return Message("635519ce-6fa8-4ae2-86bd-fe402d211d28", value)

    @staticmethod
    def MLong(value):
        return Message.MInt(value)

    @staticmethod
    def MInt(value):
        if not isinstance(value, int):
            raise TypeError, 'value param is not int type'

        return Message("38d7d249-6104-4407-9a38-5bde09e26581", value)

    @staticmethod
    def MDouble(value):
        if not isinstance(value, float):
            raise TypeError, 'value param is not float type'

        return Message("ba3b07cf-af92-4754-a663-f385c12295fb", value)

    @staticmethod
    def MFloat(value):
        return MDouble(value)

    @staticmethod
    def MList(*params):
        l = [param for param in params if isinstance(param, Message)]
        return l

class RPCResult(Message):
    def __init__(self, method, session):
        if not isinstance(method, (str, unicode)):
            raise TypeError, 'method param is not str type'

        if not isinstance(session, (str, unicode, UUID)):
            raise TypeError, 'session param is not str or UUID type'

        Message.__init__(self, 'c7915151-3c57-4507-abc9-7e1293ba134d', {})
        self.method = method
        if not isinstance(session, UUID):
            self.session = session
        else:
            self.session = UUID(session)


    def Add(self, key, value):
        # """
        # 不再将基本类型转化为对象
        if isinstance(value, (str, unicode)):
            value = Message.MString(value)
        elif isinstance(value, int):
            value = Message.MInt(value)
        elif isinstance(value, float):
            value = Message.MFloat(value)
        elif isinstance(value, list):
            value = Message.MList(value)
        elif isinstance(value, UUID):
            value = Message.MString(str(value))

        if not isinstance(value, Message):
            raise TypeError, 'message param is not Message type'
        # """
        self.value[key] = value.Return();

    def Return(self, errcode):
        if not isinstance(errcode, int):
            raise TypeError, 'errcode param is not int type'

        return {
            "Type"  : str(self.type),
            "Method" : self.method,
            "Session" : str(self.session),
            "ErrorCode" : errcode,
            "Results" : self.value
        }



service_instance = None

address2user = {}
userSession = {
    # user : {
    #     session
    #     address
    #}
}

def Login(service, mail):
    Session = mail["Session"]
    result = RPCResult('Login', Session)
    source = mail.source()
    sess = mail.session()

    GameData = {}

    GameData["Health"] = 100
    GameData["Defense"] = 0
    GameData["Second"] = 120
    GameData["Bullet"] = 30
    GameData["Money"] = 0

    def getMoney(service, mail):
        GameData["Money"] = mail['result']
        result.Add("Health", GameData["Health"])
        result.Add("Defense", GameData["Defense"])
        result.Add("Second", GameData["Second"])
        result.Add("Bullet", GameData["Bullet"])
        result.Add("Money", GameData["Money"])
        service.response(source, sess, result.Return(0));

    def getBullet(service, mail):
        GameData["Bullet"] = mail['result']
        service.request('cache', callback = getMoney, CMD = 'GET', key = 'user.' + user + '.Money')

    def getSecond(service, mail):
        GameData["Second"] = mail['result']
        service.request('cache', callback = getBullet, CMD = 'GET', key = 'user.' + user + '.Bullet')

    def getDefense(service, mail):
        GameData["Defense"] = mail['result']
        service.request('cache', callback = getSecond, CMD = 'GET', key = 'user.' + user + '.Second')

    def getHealth(service, mail):
        GameData["Health"] = mail['result']
        service.request('cache', callback = getDefense, CMD = 'GET', key = 'user.' + user + '.Defense')

    def getUserInfo(service, mail):
        GameData["Cookie"] = userSession[user]['cookie']
        result.Add("Cookie", GameData["Cookie"])
        

        if mail['result'] is not None:
            service.request('cache', callback = getHealth, CMD = 'GET', key = 'user.' + user + '.Health')
        else:
            service.send('log', log = 'new user ' + user)
            service.send('cache', CMD = 'SET', key = 'user.' + user, value = str(GameData["Cookie"]))
            service.send('cache', CMD = 'SET', key = 'user.' + user + '.Health', value = GameData["Health"])
            service.send('cache', CMD = 'SET', key = 'user.' + user + '.Defense', value = GameData["Defense"])
            service.send('cache', CMD = 'SET', key = 'user.' + user + '.Second', value = GameData["Second"])
            service.send('cache', CMD = 'SET', key = 'user.' + user + '.Bullet', value = GameData["Bullet"])
            service.send('cache', CMD = 'SET', key = 'user.' + user + '.Money', value = GameData["Money"])
            result.Add("Health", GameData["Health"])
            result.Add("Defense", GameData["Defense"])
            result.Add("Second", GameData["Second"])
            result.Add("Bullet", GameData["Bullet"])
            result.Add("Money", GameData["Money"])
            service.response(source, sess, result.Return(0));

    
    user = str(mail["Params"]["Username"])
    if user not in userSession:
        userSession[user] = {}
    userSession[user]['address'] = mail.dest()
    userSession[user]['cookie'] = uuid1()
    address2user[mail.dest()] = user
    service.send('log', log = user + ' login success')
    service.request('cache', callback = getUserInfo, CMD = 'GET', key = 'user.' + user)

def SaveGameData(service, mail):
    if mail.dest() in address2user:
        user = address2user[mail.dest()]

        Health = mail["Params"]["Health"]
        Defense = mail["Params"]["Defense"]
        Second = mail["Params"]["Second"]
        Bullet = mail["Params"]["Bullet"]
        Money = mail["Params"]["Money"]

        service.send('cache', CMD = 'SET', key = 'user.' + user + '.Health', value = Health)
        service.send('cache', CMD = 'SET', key = 'user.' + user + '.Defense', value = Defense)
        service.send('cache', CMD = 'SET', key = 'user.' + user + '.Second', value = Second)
        service.send('cache', CMD = 'SET', key = 'user.' + user + '.Bullet', value = Bullet)
        service.send('cache', CMD = 'SET', key = 'user.' + user + '.Money', value = Money)

Method = {            
    'Login'   : Login,   
    'Logout'  : Login,
    'SaveGameData' : SaveGameData
}

def init(service):
    global service_instance
    service_instance = service
    service.send('log', log = 'MYCS service is initializing')
    service.listen(7777, 'json')
    
def dispatch(service, mail):
    if mail.isOneWay():
        m = mail['Method']
        if m in Method:
            Method[m](service, mail)
        
def release(service):
    service.send('log', log = 'MYCS service is releasing')