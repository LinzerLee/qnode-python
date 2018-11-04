#-*- coding:utf-8 –*-

'''
创建时间 2017年12月19日

@author: linzer
'''

__version__ = '1.0.0'
__all__ = [
    'Timestamp', 'Timer', 'TimerManager', 'Channel',
    'Demultiplexer', 'EventLoop', 'Connection',
    'Acceptor', 'Connector'
]

__author__ = 'Linzer Lee <Linzer_Lee@hotmail.com>'

from multiprocessing import Pipe
import sys, time, heapq, socket, struct, json

try:
    from select import select as _mulplex
except ImportError: pass
else: _mulplex_type = 'select'

try:
    from select import epoll as _mulplex
except ImportError: pass
else: _mulplex_type = 'epoll'
   
try:
    from select import kqueue as _mulplex
except ImportError: pass
else: _mulplex_type = 'kqueue'

if None == _mulplex:
    print 'platment is not suppored'
    sys.exit()

import select

def enum(**enums):
    return type('Enum', (), enums)

class Timestamp(object):
    """时间戳
    
    """
    MICRO_SECOND_PER_SECOND = 1000 * 1000
    
    @staticmethod
    def invaild():
        ts = Timestamp()
        ts.us = 0
        return ts
    
    @staticmethod
    def now():
        return Timestamp()
    
    @staticmethod
    def sec2us(sec):
        return int(round(sec * Timestamp.MICRO_SECOND_PER_SECOND))
    
    @staticmethod
    def format2ts(fmt):
        """YYYY-MM-DD HH:MM:SS.UUUUUU
        
        """
        ts = Timestamp.invaild()
        sec = time.mktime(time.strptime(fmt[:19], "%Y-%m-%d %H:%M:%S")) + \
                float(fmt[20:]) / Timestamp.MICRO_SECOND_PER_SECOND
        ts.delaySeconds(sec)
        
        return ts
    
    def __init__(self, us = None):
        if us is None:
            us = Timestamp.sec2us(time.time())
        self.us = us
    
    def delay(self, us):
        self.us += us
    
    def delaySeconds(self, sec):
        self.us += Timestamp.sec2us(sec)
    
    def diff(self, ts):
        if not isinstance(ts, Timestamp):
            raise TypeError, 'ts param is not Timestamp type'
        
        return float(self.us - ts.us)
        
    def diffSeconds(self, ts):
        return self.diff(ts) / Timestamp.MICRO_SECOND_PER_SECOND
    
    def unixTime(self):
        return self.us
    
    def year(self):
        lt = self.us / Timestamp.MICRO_SECOND_PER_SECOND
        return time.localtime(lt)[0]
    
    def month(self):
        lt = self.us / Timestamp.MICRO_SECOND_PER_SECOND
        return time.localtime(lt)[1]
    
    def day(self):
        lt = self.us / Timestamp.MICRO_SECOND_PER_SECOND
        return time.localtime(lt)[2]
    
    def hour(self):
        lt = self.us / Timestamp.MICRO_SECOND_PER_SECOND
        return time.localtime(lt)[3]
     
    def minute(self):
        lt = self.us / Timestamp.MICRO_SECOND_PER_SECOND
        return time.localtime(lt)[4]
    
    def second(self):
        lt = self.us / Timestamp.MICRO_SECOND_PER_SECOND
        return time.localtime(lt)[5]
               
    def format(self):
        """YYYY-MM-DD HH:MM:SS.UUUUUU
        
        """
        lt = self.us / Timestamp.MICRO_SECOND_PER_SECOND
        us = self.us % Timestamp.MICRO_SECOND_PER_SECOND
        
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(lt)) + ('.%06d' % us)
    
    def isvaild(self):
        return self.us != 0
        
    def __str__(self):
        seconds = self.us / Timestamp.MICRO_SECOND_PER_SECOND
        microseconds = self.us % Timestamp.MICRO_SECOND_PER_SECOND
        return '%d.%06d' % (seconds, microseconds)
    
    def __repr__(self):
        return str(self.us)

class TimerId(object):
    """计时器ID
    
    内部使用，一个timer从创建到结束，其TimerId可能会变化，只能通过Timer唯一表示一个计时器
    """
    def __init__(self, id, timer):
        if not isinstance(id, int) and not isinstance(id, long):
            raise TypeError, 'id param is not int or long type'
        
        if not isinstance(timer, Timer):
            raise TypeError, 'timer param is not Timer type'
        
        self._id = id
        self._timer = timer
        self._tuple = (self._id, self._timer)
    
    def id(self):
        return self._id
    
    def timer(self):
        return self._timer
    
    def tuple(self):
        return self._tuple
    
    @staticmethod
    def tuple2timerid(tuple):
        return TimerId(tuple[0], tuple[1])
        
class Timer(object):
    """计时器
    
    """
    __globalSequence = 0
    MAX_SEQ = 10000
    
    @classmethod
    def __genSequence(cls):
        """ 0 ~ MAX_SEQ-1
        """
        cls.__globalSequence += 1
        cls.__globalSequence %= Timer.MAX_SEQ
        return cls.__globalSequence
        
    
    def __init__(self, handler, when, interval):
        if not callable(handler):
            raise TypeError, 'handler param is not callable object'
        
        if not isinstance(when, Timestamp):
            raise TypeError, 'when param is not Timestamp type'
        
        self._handler = handler
        self._expiration = when
        self._interval = interval
        self._repeat = interval > 0.000001
        self._sequence = Timer.__genSequence()
        self._timerid = TimerId(self.identity(), self)
    
    def expiration(self):
        return self._expiration
    
    def identity(self):
        return self._expiration.us * Timer.MAX_SEQ + self._sequence
        
    def timerid(self):
        return self._timerid
        
    def isvaild(self):
        return self._expiration.isvaild()
        
    def run(self):
        self._handler()

    def restart(self):
        if self._repeat:
            expir = Timestamp.now()
            expir.delaySeconds(self._interval)
            self._expiration = expir
            self._sequence = Timer.__genSequence()
            self._timerid = TimerId(self.identity(), self)
        else:
            self._expiration = Timestamp.invaild()
        
class TimerManager(object):
    """计时器管理器
    
    用来管理计时器以及事件处理器
    """
    
    def __init__(self):
        self._timerPool = []
        
    def timeout(self):
        """default timeout is None
        """
        timeout = None
        if len(self._timerPool) > 0:
            now = Timestamp.now()
            timerid = TimerId.tuple2timerid(self._timerPool[0])
            timeout = timerid.timer().expiration().diffSeconds(now)
            timeout = 0 if timeout <= 0 else timeout
        
        return timeout
    
    def handleExpired(self):
        while len(self._timerPool) > 0 and self.timeout() == 0:
            _2tuple = heapq.heappop(self._timerPool)
            timerid = TimerId.tuple2timerid(_2tuple)
            timer = timerid.timer()
            timer.run()
            timer.restart()
            if timer.isvaild():
                heapq.heappush(self._timerPool, timer.timerid().tuple())
        
    def addTimer(self, handler, when, interval):
        timer = Timer(handler, when, interval)
        heapq.heappush(self._timerPool, timer.timerid().tuple())
        return timer
            
    def cancelTimer(self, timer):
        if not isinstance(timer, Timer):
            raise TypeError, 'timer param is not Timer type'
        
        heapq.heapreplace(self._timerPool, timer.timerid().tuple())
        
Event = enum(NONE = 0, READ = 1, WRITE = 2, ERROR = 4)

class Channel(object):
    """事件通道
    
    负责调整感兴趣事件源的事件
    """
    def __init__(self, eventloop, handle):
        
        if not isinstance(eventloop, EventLoop):
            raise TypeError, 'mulplex param is not EventLoop type'
        
        self._eventloop = eventloop
        self._handle = handle
        if isinstance(handle, int):
            self._fd = handle
        else:
            self._fd = handle.fileno()
        self._events = Event.NONE
        self._revents = Event.NONE
        self._readHandler = None
        self._writeHandler = None
        self._errorHandler = None
        self._closeHandler = None
        
    def enableRead(self):
        self._events |= Event.READ
        self._eventloop.update(self)

    def disableRead(self):
        self._events &= ~Event.READ
        self._eventloop.update(self)
    
    def enableWrite(self):
        self._events |= Event.WRITE
        self._eventloop.update(self)

    def disableWrite(self):
        self._events &= ~Event.WRITE
        self._eventloop.update(self)
    
    def enableError(self):
        self._events |= Event.ERROR
        self._eventloop.update(self)
    
    def disableError(self):
        self._events &= ~Event.ERROR
        self._eventloop.update(self)
    
    def enable(self, flag):
        self._events |= flag
        self._eventloop.update(self)
    
    def disable(self, flag):
        self._events &= ~flag
        self._eventloop.update(self)
    
    def enableAll(self):
        self._events |= (Event.READ | Event.WRITE | Event.ERROR)
        self._eventloop.update(self)
    
    def disableAll(self):
        self._events &= ~(Event.READ | Event.WRITE | Event.ERROR)
        self._eventloop.update(self)
    
    def canRead(self):
        return bool(self.events & Event.READ)
    
    def canWrite(self):
        return bool(self.events & Event.WRITE)
    
    def canError(self):
        return bool(self.events & Event.ERROR)
    
    def fileno(self):
        return self._fd
    
    def handle(self):
        return self._handle
    
    def events(self):
        return self._events
          
    def setReadHandler(self, handler):
        if not callable(handler):
            raise TypeError, 'handler is not callable'
        
        self._readHandler = handler
    
    def setWriteHandler(self, handler):
        if not callable(handler):
            raise TypeError, 'handler is not callable'
        
        self._writeHandler = handler
    
    def setErrorHandler(self, handler):
        if not callable(handler):
            raise TypeError, 'handler is not callable'
        
        self._errorHandler = handler
    
    def setCloseHandler(self, handler):
        if not callable(handler):
            raise TypeError, 'handler is not callable'
        
        self._closeHandler = handler
        
    def handleEvent(self, revent):
        self._revents = revent
        ts = Timestamp.now()
        if self._revents & Event.READ:
            self._handleRead(ts)
        
        if self._revents & Event.WRITE:
            self._handleWrite(ts)
            
        if self._revents & Event.ERROR:
            self._handleError(ts)
            
    def _handleRead(self, ts):
        if self._readHandler is not None:
            self._readHandler(self, ts)  
            
    def _handleWrite(self, ts):
        if self._writeHandler is not None:
            self._writeHandler(self, ts)  
            
    def _handleError(self, ts):
        if self._errorHandler is not None:
            self._errorHandler(self, ts) 
        self.handleClose(ts)
            
    def close(self):
        """
        
        Connection未创建由client负责关闭，否则由Connection负责关闭
        """
        ts = Timestamp.now()
        if self._closeHandler is not None:
            self._closeHandler(self, ts) 
        
        self.disableAll()
        self._eventloop.unregister(self._handle)
        self._handle.close()
                   
class Demultiplexer(object):
    """事件分离器
    
    将事件源的IO事件分离出来，并分发到对应的事件处理器
    Windows环境下采用select
    Linux环境下采用epoll
    其他类Unix环境采用kqueue
    """
    def __init__(self):    
        self._channels = {}
        if 'select' == _mulplex_type:
            self._mulplex = _mulplex
            self._rlist = set()
            self._wlist = set()
            self._xlist = set()
        else:
            self._mulplex = _mulplex()
               
    def register(self, channel):
        if not isinstance(channel, Channel):
            raise TypeError, 'channel is not Channel type'
          
        fd = channel.fileno()
        if fd in self._channels:
            raise RuntimeError, 'channel already register on Demultiplexer'
             
        channel.disableAll()
        channel.enableRead()
        self._channels[fd] = channel
        if 'select' == _mulplex_type:
            self._rlist.add(fd)
        elif 'epoll' == _mulplex_type:
            self._mulplex.register(fd, select.EPOLLIN | select.EPOLLHUP) 
        elif 'kqueue' == _mulplex_type:
            changelist = []
            changelist.append(select.kevent(fd, select.KQ_FILTER_READ, select.KQ_EV_ADD))
            changelist.append(select.kevent(fd, select.KQ_FILTER_WRITE, select.KQ_EV_ADD))
            changelist.append(select.kevent(fd, select.KQ_FILTER_WRITE, select.KQ_EV_DISABLE))
            self._mulplex.control(changelist, 0)
        
        return True
    
    def unregister(self, channel):
        if not isinstance(channel, Channel):
            raise TypeError, 'channel is not Channel type'
          
        fd = channel.fileno()
        if fd not in self._channels:
            raise RuntimeError, 'channel has not register, can\'t be unregistered'
        
        channel.disableAll()
        if 'select' == _mulplex_type:
            if fd in self._rlist:
                self._rlist.remove(fd)
            
            if fd in self._wlist:   
                self._wlist.remove(fd)
                
            if fd in self._xlist:   
                self._xlist.remove(fd)
        elif 'epoll' == _mulplex_type:
            self._mulplex.unregister(fd) 
        elif 'kqueue' == _mulplex_type:
            changelist = []
            changelist.append(select.kevent(fd, select.KQ_FILTER_READ, select.KQ_EV_DELETE))
            changelist.append(select.kevent(fd, select.KQ_FILTER_WRITE, select.KQ_EV_DELETE))
            self._mulplex.control(changelist, 0)
          
        del self._channels[fd]
        return True
        
    def update(self, channel):
        if not isinstance(channel, Channel):
            raise TypeError, 'channel is not Channel type'
          
        fd = channel.fileno()
        if fd not in self._channels:
            return
        
        event = channel.events()
        if 'select' == _mulplex_type:
            if fd in self._rlist:
                self._rlist.remove(fd)
            
            if fd in self._wlist:   
                self._wlist.remove(fd)
                
            if fd in self._xlist:   
                self._xlist.remove(fd)
            
            if event & Event.READ:
                self._rlist.add(fd)
                
            if event & Event.WRITE:
                self._wlist.add(fd)
                
            if event & Event.ERROR:
                self._xlist.add(fd)
        elif 'epoll' == _mulplex_type:
            e = 0
            if event & Event.READ:
                e |= select.EPOLLIN | select.EPOLLHUP 
                
            if event & Event.WRITE:
                e |= select.EPOLLOUT
                
            if event & Event.ERROR:
                e |= select.EPOLLERR
                
            self._mulplex.modify(fd, e)
        elif 'kqueue' == _mulplex_type:
            changelist = []
            if event & Event.READ:
                changelist.append(select.kevent(fd, select.KQ_FILTER_READ, select.KQ_EV_ENABLE))
            else:
                changelist.append(select.kevent(fd, select.KQ_FILTER_READ, select.KQ_EV_DISABLE))
             
            if event & Event.WRITE:
                changelist.append(select.kevent(fd, select.KQ_FILTER_WRITE, select.KQ_EV_ENABLE))
            else:
                changelist.append(select.kevent(fd, select.KQ_FILTER_WRITE, select.KQ_EV_DISABLE))
            #kqueue不响应Error事件  
            self._mulplex.control(changelist, 0)
    
    def wait(self, timeout = None):
        """default timeout is None, means wait forever
        
        """
        events = {}
        if 'select' == _mulplex_type:
            rlist = [elm for elm in self._rlist]
            wlist = [elm for elm in self._wlist]
            xlist = [elm for elm in self._xlist]
            rfd, wfd, efd = self._mulplex(rlist, wlist, xlist, timeout)
            for fd in rfd:
                events[fd] = Event.READ if fd not in events else events[fd] | Event.READ
            
            for fd in wfd:
                events[fd] = Event.WRITE if fd not in events else events[fd] | Event.WRITE
            
            for fd in efd:
                events[fd] = Event.ERROR if fd not in events else events[fd] | Event.ERROR      
        elif 'epoll' == _mulplex_type:
            if timeout is None:
                timeout = -1
            l = self._mulplex.poll(timeout) 
            # (fd, event) 2-tuples
            for t in l:
                fd = t[0]
                event = t[1]
                if event & (select.EPOLLIN | select.EPOLLHUP):
                    events[fd] = Event.READ if fd not in events else events[fd] | Event.READ
                
                if event & select.EPOLLOUT:
                    events[fd] = Event.WRITE if fd not in events else events[fd] | Event.WRITE
                    
                if event & select.EPOLLERR:
                    events[fd] = Event.ERROR if fd not in events else events[fd] | Event.ERROR
        elif 'kqueue' == _mulplex_type:
            # kevent
            # kqueue没有永久阻塞
            kevents = self._mulplex.control(None, 1000, timeout)
            for kevent in kevents:
                fd = kevent.ident
                filter = kevent.filter
                if filter == select.KQ_FILTER_READ:
                    events[fd] = Event.READ if fd not in events else events[fd] | Event.READ
                
                if filter == select.KQ_FILTER_WRITE:
                    events[fd] = Event.WRITE if fd not in events else events[fd] | Event.WRITE
                
        return events
  
class EventLoop(object):
    """事件反应器
    
    基于Reactor模式的事件反应器
    """
    def __init__(self):
        self._timerManager = TimerManager()
        self._mulplex = Demultiplexer()
        self._channels = {}
        self._pendingHandlers = []
        self._wakeupHandles = []
        rpipe, wpipe = self._pipe()
        self._rpipe = rpipe
        self._wpipe = wpipe
        self._wakeupChannel = self.register(rpipe)
        self._wakeupChannel.setReadHandler(self.__defaultWakeupHandler)
        self._isRunning = False
    
    def _pipe(self):
        if 'select' == _mulplex_type:
            rpipe = socket.socket()
            rpipe.bind(('127.0.0.1', 4444))
            rpipe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            rpipe.listen(0)
            wpipe = socket.socket()
            wpipe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            wpipe.setblocking(0)
            wpipe.connect_ex(('127.0.0.1', 4444))
            sock, addr = rpipe.accept()
            rpipe.close()
            rpipe = sock
            return rpipe, wpipe
        else:
            return Pipe()
    
    def wakeup(self):
        self._wpipe.send('EventLoop Wakeup!')
           
    def __defaultWakeupHandler(self, channel, ts):
        if 'select' == _mulplex_type:
            channel.handle().recv(1024)
        else:
            channel.handle().recv()
        
    def register(self, handle):
        if handle in self._channels:
            raise RuntimeError, 'handle already register on EventLoop'
        
        channel = Channel(self, handle)
        channel.setReadHandler(EventLoop.__defaultReadHandler)
        channel.setErrorHandler(EventLoop.__defaultErrorHandler)
        channel.setCloseHandler(EventLoop.__defaultCloseHandler)
        fd = channel.fileno()
        self._channels[fd] = channel
        self._mulplex.register(channel)
        
        return channel
    
    def unregister(self, handle):
        """一般由Channel.close调用，用户不需要自己调用
        """
        fd = handle.fileno()
        if fd not in self._channels:
            raise RuntimeError, 'handle has not register, can\'t be unregistered'
        
        channel = self._channels[fd]
        self._mulplex.unregister(channel)
        del self._channels[fd]
     
    def update(self, channel):
        self._mulplex.update(channel)
        # fixme: 修复了Windows环境下修改监听事件类型后select无法应用问题
        self.wakeup()
    
    def oneloop(self, timeout = None):
        events = self._mulplex.wait(timeout)
        itr = events.iteritems()
        for fd, event in itr:
            self._channels[fd].handleEvent(event) 
        
        self._timerManager.handleExpired() 
        self.handlePending()
    
    def loop(self):
        self._isRunning = True
        while self._isRunning:
            timeout = self._timerManager.timeout()
            self.oneloop(timeout)
    
    def stop(self):
        self._isRunning = False
        self.wakeup()
    
    def pendHandler(self, handler):
        if not callable(handler):
            raise TypeError, 'handler param is not callable object'
        
        self._pendingHandlers.append(handler)
    
    def timerAt(self, handler, when):
        if not callable(handler):
            raise TypeError, 'handler param is not callable object'
        
        timer = self._timerManager.addTimer(handler, when, .0)
        self.wakeup()
        return timer
        
    def timerAfter(self, handler, delaySec):
        when = Timestamp.now()
        when.delaySeconds(delaySec)
        return self.timerAt(handler, when)
        
    def timerEvery(self, handler, interval):
        if not callable(handler):
            raise TypeError, 'handler param is not callable object'
        
        when = Timestamp.now()
        when.delaySeconds(interval)
        timer = self._timerManager.addTimer(handler, when, interval)
        self.wakeup()
        
        return timer
     
    def timerCancel(self, timer):
        if not isinstance(timer, Timer):
            raise TypeError, 'timer param is not Timer type'
        
        self._timerManager.cancelTimer(timer)   
    
    def handlePending(self):
        # 待处理的例程有可能回挂起新的例程
        handlers = self._pendingHandlers
        self._pendingHandlers = []
        for handler in handlers:
            handler()
        
    @staticmethod
    def __defaultReadHandler(channel, ts):
        print 'Eventloop __defaultReadHandler'
        # 默认丢掉数据，避免不断出发READ事件
        try:
            channel.handle().recv(1024)
        except:
            pass
        
    @staticmethod
    def __defaultCloseHandler(channel, ts):
        # 不要在里面关闭handle，channel会负责关闭，重复关闭会导致事件分发器异常
        # print 'Eventloop __defaultCloseHandler'
        pass
    
    @staticmethod
    def __defaultErrorHandler(channel, ts):
        # 不要在里面关闭handle，channel会负责关闭，重复关闭会导致事件分发器异常
        # print 'Eventloop __defaultErrorHandler'
        pass
     
class Connection(object):
    """TCP连接
    
    """
    # RPC序列化协议
    _protocols = {                                      \
        'raw' : {                                       \
            'encode' : lambda obj : str(obj),           \
            'decode' : lambda _str : _str               \
        },                                              \
        'json' : {                                      \
            'encode' : lambda obj : json.dumps(obj),    \
            'decode' : lambda _str : json.loads(_str)   \
        }
    }
    
    @classmethod
    def registerProtocol(cls, name, encodeHandler, decodeHandler):
        if not callable(encodeHandler):
            raise TypeError, 'encodeHandler param is not callable object'
        
        if not callable(decodeHandler):
            raise TypeError, 'decodeHandler param is not callable object'
        
        cls._protocols[name] = { 'encode' : encodeHandler, \
                                 'decode' : decodeHandler }
    
    @classmethod
    def unregisterProtocol(cls, name):
        del cls._protocols[name]
    
    def __init__(self, eventloop, channel, proto='raw'):
        if not isinstance(eventloop, EventLoop):
            raise TypeError, 'eventloop param is not EventLoop type'
        
        if not isinstance(channel, Channel):
            raise TypeError, 'channel param is not Channel type'
        
        channel.handle().setblocking(0)
        self._proto = proto
        self._input = bytearray()
        self._output =  bytearray()
        self._eventloop = eventloop
        self._channel = channel
        self._channel.setReadHandler(self._handleRead)
        self._channel.setWriteHandler(self._handleWrite)
        self._channel.setErrorHandler(self._handleError)
        self._channel.setCloseHandler(self._handleClose)
        self._highWaterMark = 64 * 1024 * 1024
        self._connStateHandler = Connection.__defaultConnStateHandler
        self._msgReachHandler = Connection.__defaultMsgReachHandler
        self._writeComplHandler = Connection.__defaultWriteComplHandler
        self._hwmHandler = Connection.__defaultHWMHandler
        self._connCloseHandler = Connection.__defaultConnCloseHandler
        self._packHandler = Connection.__defaultPackHandler
        self._unpackHandler = Connection.__defaultUnpackHandler
    
    def peerAddress(self):
        return self._channel.handle().getpeername()
    
    def selfAddress(self):
        return self._channel.handle().getsockname()
    
    def setPacker(self, packHandler, unpackHandler):
        self._packHandler = packHandler
        self._unpackHandler = unpackHandler
    
    def setProtocol(self, proto):
        self._proto = proto
        
    def channel(self):
        return self._channel
    
    def inputBuffer(self):
        return self._input
    
    def outputBuffer(self):
        return self._output
    
    def encode(self, obj):
        encodeHandler = Connection._protocols['raw']['encode']
        if self._proto in Connection._protocols:
            encodeHandler = Connection._protocols[self._proto]['encode']
            
        return encodeHandler(obj)
    
    def decode(self, msg):
        if msg is None:
            return None
        
        if not isinstance(msg, str):
            raise TypeError, 'msg param is not str type'
          
        encodeHandler = Connection._protocols['raw']['decode']
        if self._proto in Connection._protocols:
            encodeHandler = Connection._protocols[self._proto]['decode']
            
        return encodeHandler(msg)
    
    def pack(self, msg):
        """打包函数
        
        msg参数是str类型
        返回的数据是bytearray类型
        """
        return self._packHandler(msg)
    
    def unpack(self, _bytes):
        """分包函数
        
        _bytes参数是bytearray类型
        返回的的数据是str类型
        """
        return self._unpackHandler(_bytes)
       
    def send(self, obj):
        self._output.extend(self.pack(self.encode(obj)))
        self._channel.enableWrite()
        self._writeComplHandler(self, Timestamp.now())
    
    def close(self):
        ts = Timestamp.now()
        self._connCloseHandler(self, ts)
        self._connStateHandler(self, ts)
        self.channel().close()
        
    def setConnStateHandler(self, handler):
        if not callable(handler):
            raise TypeError, 'handler param is not callable object'
        self._connStateHandler = handler
    
    def setMsgReachHandler(self, handler):
        if not callable(handler):
            raise TypeError, 'handler param is not callable object'
        self._msgReachHandler = handler
    
    def setWriteComplHandler(self, handler):
        if not callable(handler):
            raise TypeError, 'handler param is not callable object'
        self._writeComplHandler = handler
    
    def setConnCloseHandler(self, handler):
        if not callable(handler):
            raise TypeError, 'handler param is not callable object'
        self._connCloseHandler = handler
    
    def _handleRead(self, channel, ts):
        sock = channel.handle()
        try:
            data = sock.recv(1024)
        except:
            self.close()
        else:
            if len(data) > 0:
                self._input.extend(data)
                try:
                    msg = self.decode(self.unpack(self._input))
                    while msg is not None:
                        self._msgReachHandler(self, msg, Timestamp.now())
                        msg = self.decode(self.unpack(self._input))
                except: pass
            else:
                self.close()
    
    def _handleWrite(self, channel, ts):
        sock = channel.handle()
        try:
            size = sock.send(self._output)
        except:
            channel.handleError(ts)
        finally:
            if len(self._output) == size:
                channel.disableWrite()
            
            while size > 0:
                self._output.pop(0)
                size -= 1
    
    def _handleError(self, channel, ts):
        pass
    
    def _handleClose(self, channel, ts):
        pass
    
    @staticmethod
    def __defaultPackHandler(msg):
        """TLV Protocol
        
        Magic(4B):      1A2B3C4D
        Checksum(2B):
        Type(2B):       raw          1
                        json         2
                        xml          3
                        protobuf     4
        Length(4B):     size
        Value(size)           
        """
        # type字段由msg类型决定
        fmt = '!IHHI%ds' % len(msg)
        packer = struct.Struct(fmt)
        value = (0x1A2B3C4D, Connection.checksum(msg), 1, len(msg) + 12, msg)
        data = bytearray()
        data.extend(packer.pack(*value))

        return data
    
    @staticmethod
    def __defaultUnpackHandler(buf):
        if len(buf) >= 12:
            fmt = '!IHHI'
            packer = struct.Struct(fmt)
            magic, checksum, _type, length = packer.unpack(buf[:12])
            msg = None
            if 0x1A2B3C4D == magic:
                if len(buf) >= length:
                    msg = str(buf[12:length])
                    size = length
                    if checksum != Connection.checksum(msg):
                        magic = bytearray()
                        magic.extend(struct.pack('!I', 0x1A2B3C4D))
                        size = buf.find(magic)
                        msg = None
                    
                    while size > 0:
                        buf.pop(0)
                        size -= 1
                        
            return msg
    
    @staticmethod
    def checksum(data):
        if isinstance(data, str):
            tmp = bytearray()
            tmp.extend(data)
            data = tmp
        
        if not isinstance(data, bytearray):
            raise TypeError, 'msg param is not str type or bytearray type'
        
        checksum = 0
        size = len(data)
        index = 0
        while index + 2 < size:
            checksum += struct.unpack('!H', data[index:index+2])[0]
            index += 2
        
        index = size - index
        if index == 1:
            checksum += struct.unpack('!B', data[size-1:size])[0]
        
        checksum = (checksum >> 16) + (checksum & 0xffff)
        checksum = checksum + (checksum>>16)
        
        return ~checksum & 0xffff
            
    
    @staticmethod
    def __defaultConnStateHandler(conn, ts):
        # print '__defaultConnStateHandler'
        pass
    
    @staticmethod
    def __defaultMsgReachHandler(conn, msg, ts):
        print '__defaultMsgReachHandler'
    
    @staticmethod
    def __defaultWriteComplHandler(conn, ts):
        pass
    
    @staticmethod
    def __defaultHWMHandler(conn, ts):
        print '__defaultHWMHandler'
    
    @staticmethod
    def __defaultConnCloseHandler(conn, ts):
        pass
        
class Acceptor(object):
    """连接接收器
    
    """
    def __init__(self, eventloop, address, port):
        self._eventloop = eventloop
        self._address = address
        self._port = port
        self._handle = socket.socket()
        self._handle.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._handle.setblocking(0)
        self._handle.bind((address, port))
        self._fd = self._handle.fileno()
        self._running = False
        self._channel = None
        self._newConnHandler = Acceptor.__defaultNewConnHandler
    
    def port(self):
        return self._port
    
    def setNewConnHandler(self, handler):
        if not callable(handler):
            raise TypeError, 'handler param is not callable object'
        
        self._newConnHandler = handler
    
    def isRunning(self):
        return self._running
        
    def run(self):
        self._handle.listen(100)
        self._channel = self._eventloop.register(self._handle)
        if self._channel is None:
            raise RuntimeError, 'acceptor register eventloop faild'
        
        self._channel.setReadHandler(self._handleRead)
        self._running = True
    
    def close(self):
        self._running = False
        self._channel.close()
        del self._channel
        
    def _handleRead(self, channel, ts):
        try:
            sock, addr = channel.handle().accept()
        except OSError:
            print 'accept faild'
        else:
            conn = Connection(self._eventloop, self._eventloop.register(sock))
            conn.setMsgReachHandler(self.__defaultMsgReachHandler)
            if self._newConnHandler is not None:
                self._newConnHandler(self, conn, Timestamp.now())
                
    def __defaultMsgReachHandler(self, conn, msg, ts):
        print '__defaultMsgReachHandler'
        print '%s get msg %s' % (ts.format(), str(msg))
        
    @staticmethod       
    def __defaultNewConnHandler(acceptor, conn, ts):
        print '%s new connection' % ts.format()
        
class Connector(object):
    """连接器
    
    """
    INIT_RETRY_DELAY_MS = 500
    MAX_RETRY_DELAY_MS = 10 * 1000
    def __init__(self, eventloop, peeraddr):
        if not isinstance(eventloop, EventLoop):
            raise TypeError, 'eventloop params is not EventLoop type'
        
        if not isinstance(peeraddr, tuple):
            raise TypeError, 'address params is not tuple type'
        
        self._eventloop = eventloop
        self._peeraddr = peeraddr
        self._connection = None
        self._retryDelayMS = Connector.INIT_RETRY_DELAY_MS
        self._retryCount = 0
        self._newConnHandler = None
        self._retryHandler = None
    
    def peeraddr(self):
        return self._peeraddr
    
    def connecting(self):
        """
        
        A) 当连接建立成功时，套接口描述符变成 可写（连接建立时，写缓冲区空闲，所以可写）
        B) 当连接建立出错时，套接口描述符变成 既可读又可写（由于有未决的错误，从而可读又可写）
        """
        self._channel = self._eventloop.register(self._handle)
        self._channel.disableRead()
        self._channel.enableWrite()
        self._channel.setWriteHandler(self._checkConnState)
    
    def setRetryHandler(self, handler):
        if not callable(handler):
            raise TypeError, 'handler param is not callable object'
        self._retryHandler = handler
        
    def retry(self):
        # 不要在retry里面关闭channel，在retry之外进行
        self._retryCount += 1
        self._retryDelayMS = min(self._retryDelayMS * 2, Connector.MAX_RETRY_DELAY_MS)
        
        if self._retryHandler is not None:
            self._retryHandler(self, self._retryCount, self._retryDelayMS / 1000.0, Timestamp.now())
        del self._channel
        
        self._eventloop.timerAfter(self.connect, self._retryDelayMS / 1000.0)
    
    def connect(self):
        self._handle = socket.socket()
        self._handle.setblocking(0)
        self._fd = self._handle.fileno()
        errno = self._handle.connect_ex(self._peeraddr)
        if errno in (0, socket.errno.EINPROGRESS, socket.errno.EISCONN, socket.errno.EWOULDBLOCK):
            self.connecting()
        elif errno in (socket.errno.EINTR, socket.errno.EAGAIN,                     \
                       socket.errno.EADDRINUSE, socket.errno.EADDRNOTAVAIL,         \
                       socket.errno.ECONNREFUSED, socket.errno.ENETUNREACH):
            print 'connector connect server error %d' % errno
            # handle尚未托管给channel，connector负责关闭
            self._handle.close()
            self.retry()
        else:
            print 'connector connect server faild : %d' % errno
            # handle尚未托管给channel，connector负责关闭
            self._handle.close()
            del self._handle
            del self._fd
    
    def start(self):
        self._eventloop.pendHandler(self.connect)
        self._eventloop.wakeup()
        
    def resetRetry(self):
        self._retryDelayMS = Connector.INIT_RETRY_DELAY_MS
        self._retryCount = 0
       
    def setNewConnHandler(self, handler):
        if not callable(handler):
            raise TypeError, 'handler param is not callable'
        self._newConnHandler = handler
    
    def connection(self):
        return self._connection
     
    def _checkConnState(self, channel, ts):
        """
        再次调用connect，相应返回失败，如果错误errno是EISCONN，
        表示socket连接已经建立，否则认为连接失败
        """
        errno = self._handle.connect_ex(self._peeraddr)
        if 0 == errno:
            print 'you should not capture data, and close channel write hook'
        elif socket.errno.EISCONN == errno:
            # connect server success, then you should close this hook
            # connection will capture this hook
            self._channel.enableRead()
            self._connection = Connection(self._eventloop, self._channel)
            self.resetRetry()
            if self._newConnHandler is not None:
                self._newConnHandler(self, self._connection, Timestamp.now())
        else:
            #connector connect server error, try again
            self._channel.disableWrite()
            # Connection未创建，Client负责关闭Channel
            self._channel.close()
            self.retry()