#-*- coding:utf-8 –*-
'''
Created on 2017年12月28日

@author: linzer
'''

from functools import partial
from net import Timestamp
from framework import Context, Service, Mail

def init(service):
    print Timestamp.now().format(), 'log service is initializing'
    
def dispatch(service, mail):
    print '%s %s' % (Timestamp.now().format(), mail['log'])
        
def release(service):
    print Timestamp.now().format(), 'log service is releasing'