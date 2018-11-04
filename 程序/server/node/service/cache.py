#-*- coding:utf-8 –*-
'''
Created on 2017年12月28日

@author: linzer
'''

from functools import partial
from net import Timestamp
from framework import Context, Service, Mail
import json

db_path = None
    
db = [{}, None]

def GET(key):
    cur = db
    nodes = key.split('.')
    for node in nodes:
        if node in cur[0]:
            cur = cur[0][node]
        else:
            return None
        
    if cur != db:
        return cur[1]

def SET(key, value):
    cur = db
    nodes = key.split('.')
    for node in nodes:
        if node not in cur[0]:
            cur[0][node] = [{}, None]
        cur = cur[0][node]
        
    cur[1] = value
    json.dump(db, file(db_path, 'w'))
    
def init(service):
    global db_path
    db_path = service.getEnv('cachedb')
    service.send('log', log = 'cache service is initializing')
    try:
        global db
        db = json.load(file(db_path, 'r'))
    except ValueError:
        db = [{}, None]
    
def dispatch(service, mail):
    cmd = mail['CMD']
    if 'GET' == cmd:
        value = GET(mail['key'])
        if mail.isOneWay():
            service.send(mail.source(), result = value)  
        elif mail.isREQ():
            service.response(mail.source(), mail.session(), result = value)  
    elif 'SET' == cmd:
        SET(mail['key'], mail['value'])
        
def release(service):
    service.send('log', log = 'cache service is releasing')