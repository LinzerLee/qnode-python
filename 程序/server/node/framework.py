#-*- coding:utf-8 –*-
'''
Created on 2017年12月25日

@author: linzer
'''
from net import *
import json, sys, Queue
from _functools import partial

_DEFAULT_GROUPNAME = 'defaultgroup'

class Router(object):
    """本地服务路由组件
    
    """
    _instance = None
    _registry = {                               \
        _DEFAULT_GROUPNAME : {}                 \
    }
    _services = {}
    def __new__(cls, *args, **kwd):
        if Router._instance is None:
            Router._instance = super(Router, cls).__new__(cls, *args, **kwd)
            
        return Router._instance
    
    def update(self, sid, sname, gname = _DEFAULT_GROUPNAME):
        if gname not in Router._registry:
            Router._registry[gname] = {}
        
        if sname not in Router._registry[gname]:
            Router._registry[gname][sname] = {}
            
        Router._registry[gname][sname][sid] = {}
        Router._services[sid] = {           \
            'groupname' : gname,            \
            'shortname' : sname             \
        }
    
    def delete(self, sid):  
        if sid not in Router._services:
            return
        
        gname = Router._services[sid]['groupname']
        sname = Router._services[sid]['shortname']
        
        del Router._services[sid]
        del Router._registry[gname][sname][sid]
        if len(Router._registry[gname][sname]) == 0:
            del Router._registry[gname][sname]
            
        if len(Router._registry[gname]) == 0:
            del Router._registry[gname]
    
    def query(self, sname, gname = _DEFAULT_GROUPNAME):
        services = None
        if gname in Router._registry:
            if sname in Router._registry[gname]:
                services = Router._registry[gname][sname]
                
        return services
    
    def getRegistry(self):
        return self._registry
        
    def check(self, sid):
        return True if sid in Router._services else False
     
class Gate(object):
    """网关服务组件
    
    """
    _acceptors = {}
    _protocols = {}
    _packers = {}
    _ports = {} # port --> (serviceid, gate)
    _peeraddr2Conn = {}
    _conntors = {} # peerAddr --> conntor
    _peeraddr2NID = {}
    def __init__(self, ctx):
        self._eventloop = EventLoop()
        self._ctx = ctx
        # default standalone mode
    
    def _listen(self, host, port, sid):
        Gate._ports[port] = (sid, self)
        acceptor = Acceptor(self._eventloop, host, port)
        acceptor.setNewConnHandler(self._handleNewConn)
        Gate._acceptors[port] = acceptor 
        acceptor.run()
    
    def exchangeRemoteRoute(self, nid = None):
        registry = self._ctx.getLocalRegistry()
        rtable = {}
        for gname in registry:
            if gname not in rtable:
                rtable[gname] = {}
            for sname in registry[gname]:
                if sname not in rtable[gname]:
                    rtable[gname][sname] = []
                for sid in registry[gname][sname]:
                    if self._ctx.NID() == Service.getNIDFromSID(sid):
                        rtable[gname][sname].append(sid)
                        
        self.updateRemoteRoute('ROUTE_EXCHANGE', rtable, nid)
    
    def updateRemoteRoute(self, cmd, rtable, nid = None):
        params = {}
        params['CMD'] = cmd
        params['routes'] = rtable
        for peer in Gate._peeraddr2NID:
            _nid = Gate._peeraddr2NID[peer]
            if self._ctx.NID() == _nid:
                continue
            
            if nid is None or nid == _nid:
                cid = (_nid & 0x0000ffff) << 16 
                mail = Mail(self._ctx.CID(), cid, 0, params)
                msgObj = Mail.toRemote(mail)
                self.send(peer, msgObj)
                
                if nid == _nid:
                    return
         
    def addRemoteHost(self, peerAddr):
        if not isinstance(peerAddr, tuple):
            raise TypeError, 'peerAddr param is not tuple type'
        
        conntor = Connector(self._eventloop, peerAddr)
        Gate._conntors[peerAddr] = conntor
        conntor.setNewConnHandler(self._handleNewClusterConn)
        conntor.setRetryHandler(self._handleRetry)
        conntor.start()
     
    def clusterMode(self, localhost, peerhosts):
        if not isinstance(localhost, tuple):
            raise TypeError, 'localhost param is not tuple type'
        
        host = localhost[0]
        port = localhost[1]
        # cluster服务很特殊，serviceid等于当前节点的NID << 16
        self._listen(host, port, self._ctx.CID())
        for peer in peerhosts:
            nid = peer[2]
            peer = peer[:2]
            Gate._peeraddr2NID[peer] = nid
            # 新加入的主机应该主动连接旧的主机
            if localhost != peer: # and nid < self._ctx.NID():
                self.addRemoteHost(peer)
     
    def register(self, serviceid, port, protocol = None, packer = None):
        if not isinstance(port, int):
            raise TypeError, 'port param is not int type'
        
        if port in Gate._acceptors:
            return
        
        if protocol is not None:
            if not isinstance(protocol, str):
                raise TypeError, 'protocol param is not str type'
            Gate._protocols[port] = protocol
            
        if packer is not None:
            if not isinstance(packer, tuple):
                raise TypeError, 'packer param is not tuple type'
            Gate._packers[port] = packer
        
        self._listen('', port, serviceid)
    
    def unregister(self, port):
        if not isinstance(port, int):
            raise TypeError, 'port param is not int type'
        
        if port not in Gate._acceptors:
            raise RuntimeError, 'Gate: not register this port'
        
        acceptor = Gate._acceptors[port]
        acceptor.close()
        del Gate._acceptors[port]
                  
    def start(self):
        self._eventloop.loop()
        
    def stop(self):
        self._eventloop.stop()
    
    def send(self, dest, msgObj):
        if isinstance(dest, tuple) and dest in Gate._peeraddr2Conn:
            # 外网邮件
            conn = Gate._peeraddr2Conn[dest]
            conn.send(msgObj)
        elif isinstance(dest, (int, long)):
            # 远程服务调用邮件
            for peer in Gate._peeraddr2NID:
                if Service.getNIDFromSID(dest) == Gate._peeraddr2NID[peer]:
                    if peer in Gate._peeraddr2Conn:
                        Gate._peeraddr2Conn[peer].send(msgObj)
                    return
            print 'Not find cluster service %s' % str(dest)
        else:
            print 'No connection for address %s' % str(dest)
        
    def timerAt(self, handler, when):
        return self._eventloop.timerAt(handler, when)
        
    def timerAfter(self, handler, delaySec):
        return self._eventloop.timerAfter(handler, delaySec)
        
    def timerEvery(self, handler, interval):
        return self._eventloop.timerEvery(handler, interval)
    
    def _handleMsgReach(self, conn, msg, ts):
        port = conn.selfAddress()[1]
        serviceid = Gate._ports[port][0]
        if self._ctx.CID() == serviceid:
            # 来自其他主机的消息
            mail = Mail.fromRemote(msg)
            if self._ctx.CID() == mail.dest():
                # 接收集群之间信息交换邮件
                self._ctx.clusterMailHandler(mail) 
                return
        else:
            mail = Mail(conn.peerAddress(), serviceid, 0, msg)
        self._ctx.sendMail(mail)
    
    def _handleConnClose(self, conn, ts):
        print ts.format(), 'Connection close from', str(conn.peerAddress())
        peer = conn.peerAddress()
        del Gate._peeraddr2Conn[peer]
        if peer in Gate._conntors:
            Gate._conntors[peer].retry()
    
    def _handleNewConn(self, acceptor, conn, ts):
        port = acceptor.port()
        
        if port in Gate._protocols:
            conn.setProtocol(Gate._protocols[port])
        else:
            conn.setProtocol('json')
        
        # 保存对端地址到连接的映射
        print ts.format(), 'New connection from %s' % str(conn.peerAddress())
        Gate._peeraddr2Conn[conn.peerAddress()] = conn
        conn.setMsgReachHandler(self._handleMsgReach)
        conn.setConnCloseHandler(self._handleConnClose)
        if port in Gate._packers:
            conn.setPacker(Gate._packers[port][0], Gate._packers[port][1])
    
    def _handleNewClusterConn(self, conntor, conn, ts):
        conn.setProtocol('json')
        # 保存对端地址到连接的映射
        peeraddr = conn.peerAddress()
        print ts.format(), 'New cluster connection from %s' % str(peeraddr)
        Gate._peeraddr2Conn[peeraddr] = conn
        conn.setMsgReachHandler(self._handleMsgReach)
        conn.setConnCloseHandler(self._handleConnClose)
        self.exchangeRemoteRoute(Gate._peeraddr2NID[peeraddr])
     
    def _handleRetry(self, conntor, count, sec, ts):
        print '%s try connect to cluster %s for %d times......' % (ts.format(), str(conntor.peeraddr()), count)
        
    def __call__(self):
        self._ctx.mount(self)
        self.start()

class Mail(object):
    """消息对象
    
    """
    def __init__(self, source, dest, session = 0, params = {}):
        self._source = source
        self._dest = dest
        self._session = session
        self._params = {}
        for key in params.keys():
            self._params[key] = params[key]
        
    def setSource(self, src):
        self._source = src
    
    def source(self):
        return self._source
    
    def setDest(self, _dest):
        self._dest = _dest  
      
    def dest(self):
        return self._dest
    
    def params(self):
        return self._params
        
    def session(self):
        return self._session if self._session >= 0 else -self._session
    
    def isREQ(self):
        return self._session > 0
    
    def isREP(self):
        return self._session < 0
    
    def isOneWay(self):
        return self._session == 0
    
    def update(self, params):
        if not isinstance(params, dict):
            raise TypeError, 'params param is not dict type'
        self._params.update(params)
     
    def __call__(self, **params):
        for key in params.keys():
            self._params[key] = params[key]
     
    def __str__(self):
        s = 'From %s To %s(%d):\n' % (str(self.source()), str(self.dest()), self._session)
        for key in self._params:
            s += '\t%s : %s' % (str(key), self._params[key])
        
        return s
    
    def __getitem__(self, key): 
        if key in self._params:
            return self._params[key]

    def __setitem__(self, key, value): 
        self._params[key] = value
        
    @staticmethod       
    def toRemote(mail):
        if not isinstance(mail, Mail):
            raise TypeError, 'mail param is not Mail type'
        
        newMail = {
            'source' : mail.source(),
            'dest' : mail.dest(),
            'session' : -mail.session() if mail.isREP() else mail.session(),
            'message' : mail.params()
        }
        
        return newMail
    
    @staticmethod    
    def fromRemote(msgObj):
        if not isinstance(msgObj, dict):
            raise TypeError, 'msgObj param is not dict type'
        
        mail = Mail(msgObj['source'], msgObj['dest'], msgObj['session'], msgObj['message'])
        
        return mail
  
class ServiceManager(object):
    """服务管理器
    
    调度服务的生命周期
    """
    def __init__(self):
        self._services = {}
        
    def boostService(self, service):
        sid = service.identity()
        self._services[sid] = service
        service.init()
        
    def stopService(self, service):
        # 有bug,启动顺序可以保证，但是release顺序不能保证
        service.release()
        sid = service.identity()
        del self._services[sid]  
    
    def getAllService(self):
        return self._services.values()
    
    def stopAllService(self):
        for service in self._services.values():
            self.stopService(service)
        
    def dispatchMail(self, mail):
        service = self._services[mail.dest()]
        service.dispatch(mail)
      
class Context(object):
    """服务框架上下文
    
    """
    _instance = None
    def __new__(cls, *args, **kwd):
        if Context._instance is None:
            Context._instance = super(Context, cls).__new__(cls, *args, **kwd)
            
        return Context._instance
    
    def __init__(self):
        if not hasattr(self, '_nodeid'):
            self._env = {                               \
                'service_path' : [                      \
                    './node/service'                    \
                ]                                       \
            }
            self._isClosed = False
            self._isCanExit = False
            self._nodeid = 0
            self._clusterid = 0
            self._mailbox = {                           \
                'trash' : Queue.Queue(),                \
            }
            self._gates = {}
            self._router = Router()
            self._serviceManager = ServiceManager()
            Connection.registerProtocol('mail',                 \
                            lambda mail : Mail.dumps(mail),     \
                            lambda msg : Mail.loads(msg))
            for path in self._env['service_path']:
                sys.path.append(path)
    
    def NID(self):
        return self._nodeid
    
    def CID(self):
        return self._clusterid
    
    def addServicePath(self, path):
        if not isinstance(path, str):
            raise TypeError, 'path param is not str type'
        
        self._env['service_path'].append(path)
        sys.path.append(path)
    
    def loadConfig(self, config):
        """配置数据仅支持json格式
        
        """
        if isinstance(config, str):
            config = json.load(open(config))
        
        if not isinstance(config, dict):
            raise TypeError, 'config param is not str or dict type'
        
        self._env.update(config)
        for path in self._env['service_path']:
                sys.path.append(path)
        
        # 根据配置文件启动服务 
        # cluster mode会修改NID          
        self._clusterMode()
        # service id依赖NID  
        self._boostService()
    
    def close(self):
        # 开始关闭
        self._isClosed = True
    
    def isRunning(self):
        return not self._isClosed or not self._isCanExit
    
    def exit(self):
        services = self._serviceManager.getAllService()
        for service in services:
            self.unregister(service)
     
    def _boostService(self):
        '''根据配置文件启动服务
        '''
        if 'service' in self._env:
            for service in self._env['service']:
                self.register(Service(service))
    
    def _clusterMode(self):
        if 'localhost' in self._env:
            host = self._env['localhost'].split(':')
            nid = host[1].split('#')
            host[1] = nid[0]
            nid = int(nid[1])
            self._nodeid = nid
            self._clusterid = (nid & 0x0000ffff) << 16
            # 注册cluster mailbox
            self._mailbox[self._clusterid] = Queue.Queue()
            localhost = (host[0].strip(), int(host[1]))
            peerhosts = []
            if 'cluster' in self._env:
                for host in self._env['cluster']:
                    host = host.split(':')
                    nid = host[1].split('#')
                    host[1] = nid[0]
                    nid = int(nid[1])
                    peerhost = (host[0].strip(), int(host[1]), nid)
                    peerhosts.append(peerhost)
            
            gate = self.clusterGate()
            gate.clusterMode(localhost, peerhosts)
            
    def getEnv(self, key):
        value = None if key not in self._env else self._env[key]
        return value
    
    def setEnv(self, key, value):
        self._env[key] = value
    
    def resetEnv(self):
        self._env.clear()
    
    def gate(self):
        if len(self._gates) > 0:
            # fixme:通过负载均衡策略得到一个gate
            for gate in self._gates:
                return gate
    
    def clusterGate(self):
        return self.gate()        
    
    def mount(self, gate):
        if not isinstance(gate, Gate):
            raise TypeError, 'gate param is not Gate type'
        self._gates[gate] = {}
    
    def unmount(self, gate):
        if not isinstance(gate, Gate):
            raise TypeError, 'gate param is not Gate type'
        del self._gates[gate]
        
    def listen(self, service, port, protocol = 'mail', packer = None):
        self.gate().register(service.identity(), port, protocol, packer)
    
    def cancelListen(self, port):
        self.gate().unregister(port)
    
    def getLocalRegistry(self):
        return self._router.getRegistry()
    
    def updateServiceRoute(self, optr, sid, sname = None, gname = _DEFAULT_GROUPNAME):
        optr = optr.upper()
        rtable = {}
        if 'UPDATE' == optr:
            if sname is None:
                raise ValueError, 'sname param is not None'
            self._router.update(sid, sname, gname)
            rtable[gname] = {}
            rtable[gname][sname] = [sid]
            self.clusterGate().updateRemoteRoute('ROUTE_UPDATE', rtable)
        elif 'DELETE' == optr:
            self._router.delete(sid)
            rtable = [sid]
            self.clusterGate().updateRemoteRoute('ROUTE_DELETE', rtable)     
        
    def register(self, service):
        if not isinstance(service, Service):
            raise TypeError, 'service param is not Service type'
        _id = service.identity()
        sname = service.shortname()
        self.updateServiceRoute('update', _id, sname)
        self._mailbox[_id] = Queue.Queue()
        self._serviceManager.boostService(service)
    
    def unregister(self, service):
        if not isinstance(service, Service):
            raise TypeError, 'service param is not Service type'
        _id = service.identity()
        self.updateServiceRoute('delete', _id)
        del self._mailbox[_id]
        self._serviceManager.stopService(service)
        
    def queryOne(self, sname, gname = _DEFAULT_GROUPNAME):
        services = self._router.query(sname, gname)
        if services is not None:
            service = None
            # 本地优先策略
            for sid in services.keys():
                if service is None:
                    service = sid
                elif self.NID() == Service.getNIDFromSID(sid):
                    service = sid
                    break
                
            return service
    
    def queryAll(self, sname, gname = _DEFAULT_GROUPNAME):
        services = self._router.query(sname, gname)
        
        if services is not None:
            services = services.keys()
            
        return services

    def checkSID(self, sid):
        return self._router.check(sid)

    def clusterMailHandler(self, mail):
        if mail['CMD'] is not None:
            cmd = mail['CMD']
            rtable = mail['routes']
            if cmd in ('ROUTE_EXCHANGE', 'ROUTE_UPDATE'):
                for gname in rtable:
                    for sname in rtable[gname]:
                        for sid in rtable[gname][sname]:
                            self._router.update(sid, sname, gname)
            elif 'ROUTE_DELETE' == cmd:
                for sid in rtable:
                    self._router.delete(sid)
                           
    def sendMail(self, mail):
        if self._isClosed and not mail.isREP():
            return
        
        if not isinstance(mail, Mail):
            raise TypeError, 'mail param is not Mail type'
        
        dest = mail.dest()
        if isinstance(dest, tuple):
            # 普通外网邮件--(address, port)
            self.gate().send(dest, mail.params())
        elif self.checkSID(dest):
            # 其他邮件都需要查询路由表
            nodeid = Service.getNIDFromSID(dest)
            if self.NID() == nodeid:
                # 本节点内邮件
                self._mailbox[dest].put(mail)
            else:
                # 远程服务调用邮件
                self._mailbox[self.CID()].put(mail)
        else:
            self._mailbox['trash'].put(mail)
        
    def dispatchMail(self):
        # self._isCanExit = True
        isCanExit = True
        for sid in self._mailbox:
            if not self._mailbox[sid].empty():
                try:
                    mail = self._mailbox[sid].get_nowait()
                except: 
                    print 'dispatch mail bug'
                else:
                    isCanExit = False
                    if 'trash' == sid:
                        print 'Trash mail :\n%s' % str(mail)
                    elif self.CID() == sid:
                        msgObj = Mail.toRemote(mail)
                        self.clusterGate().send(mail.dest(), msgObj)
                    else:
                        self._serviceManager.dispatchMail(mail)
                        
        if self._isClosed and isCanExit:
            self._isCanExit = True
            
    def timerAt(self, handler, when):
        return self.gate().timerAt(handler, when)
        
    def timerAfter(self, handler, delaySec):
        return self.gate().timerAfter(handler, delaySec)
        
    def timerEvery(self, handler, interval):
        return self.gate().timerEvery(handler, interval)
    
    def runTaskQueue(self):
        # self._isClosed
        pass
           
class Service(object):
    """服务组件
    
    """
    _sequence_num = 0
    _session_num = 0
    _sessions = {}
    
    @classmethod
    def genSessionID(cls):
        cls._session_num += 1
        return cls._session_num
    
    @classmethod
    def genSequenceID(cls):
        cls._sequence_num += 1
        return cls._sequence_num
    
    @staticmethod
    def genSID(nodeid, seq):
        """Service ID
        """
        return ((nodeid & 0x0000ffff) << 16) | (seq & 0x0000ffff)
    
    @staticmethod
    def getNIDFromSID(sid):
        return (sid & 0xffff0000) >> 16

    def __init__(self, sname, gname = _DEFAULT_GROUPNAME, ctx = Context()):
        self._ctx = Context()
        self._shortname = sname
        self._groupname = gname
        self._module = __import__(sname)
        self._ctx = ctx
        self._id = Service.genSID(self._ctx.NID(), Service.genSequenceID())
    
    def shortname(self):
        return self._shortname
    
    def groupname(self):
        return self._groupname

    def identity(self):
        return self._id

    def init(self):
        if self._module is not None and hasattr(self._module, 'init'):
            self._module.init(self)
            
    def dispatch(self, mail):
        if not isinstance(mail, Mail):
            raise TypeError, 'mail param is not Mail type'
        
        if mail.isOneWay() or mail.isREQ():
            if self._module is not None and hasattr(self._module, 'dispatch'):
                self._module.dispatch(self, mail)
        elif mail.isREP():
            session = mail.session()
            if session in self._sessions:
                callback = self._sessions[session]
                del self._sessions[session]
                callback(self, mail)
            else:
                print 'Invaild session'
            
    def release(self):
        if self._module is not None and hasattr(self._module, 'release'):
            self._module.release(self)
                   
    def listen(self, port, protocol = None, packer = None):
        self._ctx.listen(self, port, protocol, packer)
    
    def cancelListen(self, port):
        self._ctx.cancelListen(port)
    
    def suspend(self, session, callback):
        if not callable(callback):
            raise TypeError, 'callback param is not callable'
        
        Service._sessions[session] = callback
        
    
    def send(self, sname, gname = _DEFAULT_GROUPNAME, **params):
        if isinstance(sname, (tuple, int, long)):
            dest = sname
        else:
            dest  = self._ctx.queryOne(sname, gname)
            
        if dest is None:
            print 'Service %s.%s is not exist' % (gname, sname)
        else:
            mail = Mail(self.identity(), dest, 0, params)
            self._ctx.sendMail(mail)
            
    @staticmethod
    def _redirectCB(source, handler, service, mail):
        mail.setDest(source)
        
        # 发送之前可能要做特殊处理
        if callable(handler):
            handler(service, mail)
        
        service._ctx.sendMail(mail)
    
    def redirect(self, mail, sname, gname = _DEFAULT_GROUPNAME, handler = None): 
        callback = partial(Service._redirectCB, mail.source(), handler)
        self.request(sname, gname, callback, **mail.params())
        
    @staticmethod
    def _default_callback(mail):
        pass
       
    def request(self, sname, gname = _DEFAULT_GROUPNAME, callback = _default_callback, **params):
        dest  = self._ctx.queryOne(sname, gname)
        if dest is None:
            print 'Service %s.%s is not exist' % (gname, sname)
        else:
            session = self.genSessionID()
            mail = Mail(self.identity(), dest, session, params)
            self._ctx.sendMail(mail)
            self.suspend(session, callback)
    
    def response(self, dest, session, kv = {}, **params):
        if not isinstance(kv, dict):
            raise TypeError, 'kv param is not dict type'
        # session如果为0，就等价于send, dest是查询后的地址
        mail = Mail(self.identity(), dest, -session)
        mail.update(kv)
        mail.update(params)
        self._ctx.sendMail(mail)
        
    def submitTask(self, handler):
        if not callable(handler):
            raise TypeError, 'handler param is not callable object'
        
    def timerAt(self, handler, when):
        return self._ctx.timerAt(handler, when)
        
    def timerAfter(self, handler, delaySec):
        return self._ctx.timerAfter(handler, delaySec)
        
    def timerEvery(self, handler, interval):
        return self._ctx.timerEvery(handler, interval)
    
    def getEnv(self, key):
        return self._ctx.getEnv(key)
    
    def setEnv(self, key, value):
        self._ctx.setEnv(key, value)
     