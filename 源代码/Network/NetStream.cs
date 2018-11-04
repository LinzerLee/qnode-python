using System;
using System.Collections.Generic;
using System.Net.Sockets;
using System.Text;
using UnityEngine;

public class NetStream {
    public enum NetState {
        Stop,
        Connecting,
        Established
    }

    // 定义事件委托
    public delegate void StateChangeEventHandler(NetState state);
    public delegate void ConnectedEventHandler();
    public delegate void DisconnectedEventHandler();
    public delegate void RetryEventHandler(float waitForSecond);
    // 声明事件
    public event StateChangeEventHandler StateChangeEvent;
    public event ConnectedEventHandler ConnectedEvent;
    public event DisconnectedEventHandler DisconnectedEvent;
    public event RetryEventHandler RetryEvent;

    private long _nextRetryTime = 0;
    private NetState _state = NetState.Stop;
    public NetState State {
        get {
            return _state;
        }

        private set {
            if(_state != value) {
                NetState old = _state;
                _state = value;
                if (null != StateChangeEvent)
                    StateChangeEvent(value);

                if(NetState.Established ==  _state) {
                    if (null != ConnectedEvent)
                        ConnectedEvent();
                } else if(NetState.Established == old) {
                    if (null != DisconnectedEvent)
                        DisconnectedEvent();
                }
            }
        }
    }

    // 13位时间戳--毫秒
    public static long Timestamp13(DateTime time) {
        DateTime startTime = TimeZone.CurrentTimeZone.ToLocalTime(new DateTime(1970, 1, 1, 0, 0, 0, 0));
        long ts = (time.Ticks - startTime.Ticks) / 10000;      
        return ts;
    }

    public NetStream(string host, int port) {
        _host = host;
        _port = port;
        _socket = new Socket(AddressFamily.InterNetwork, SocketType.Stream, ProtocolType.Tcp);
        _socket.Blocking = false;
        _socket.NoDelay = true;
        _nextRetryTime = Timestamp13(DateTime.Now);
        State = NetState.Stop;
    }

    public void Close() {
        _socket.Close();
        State = NetState.Stop;
    }

    public static bool TestNotError(SocketError error) {
        return SocketError.InProgress == error ||
                SocketError.WouldBlock == error ||
                SocketError.AlreadyInProgress == error;
    }

    private bool _TryConnect() {
        long now = Timestamp13(DateTime.Now);
        if (NetState.Established == State) {
            return true;
        }

        // 检查重连间隔
        if(now < _nextRetryTime) {
            return false;
        }

        if (NetState.Stop == State) {
            _socket.Connect(_host, _port);
            State = NetState.Connecting;
        }

        bool result = true;
        try {
            byte[] test = new byte[1];
            _socket.Receive(test, 0, 0);
            State = NetState.Established;
        } catch (SocketException e) {
            if (TestNotError(e.SocketErrorCode)) {
                State = NetState.Established;
            } else if(SocketError.IsConnected == e.SocketErrorCode) {
                result = false;
            } else {
                Debug.LogErrorFormat("Disconnected: error code {0}!", e.NativeErrorCode);
                Close();
                result = false;
            }
        }

        // 1s后尝试
        if(!result) {
            _nextRetryTime = now + 1000;
            if (null != RetryEvent)
                RetryEvent(1.0f);
        }

        return result;
    }

    private int _TrySend() {
        int size = 0;
        if (_output.Count > 0) {
            try {
                size = _socket.Send(_output.ToArray());
                _output.RemoveRange(0, size);
            } catch (SocketException e) {
                if (!TestNotError(e.SocketErrorCode)) {
                    Debug.LogErrorFormat("Disconnected: error code {0}!", e.NativeErrorCode);
                    Close();
                }
            }
        }

        return size;
    }

    private void _TryRecv() {
        byte[] recvBytes = new byte[1024];
        int size = 0;

        try {
            do {
                size = _socket.Receive(recvBytes, recvBytes.Length, 0);
                for(int i=0; i<size; ++i) {
                    _input.Add(recvBytes[i]);
                }
            } while (1024 == size);
        } catch (SocketException e) {
            if (!TestNotError(e.SocketErrorCode)) {
                Debug.LogErrorFormat("Disconnected: error code {0}!", e.NativeErrorCode);
                Close();
            }
        }
    }

    public void Send(Message message) {
        _output.AddRange(message.Serialize());
    }

    public List<Message> Receive() {
        if(NetState.Established == State)
            return Message.Unserialize(_input);

        return null;
    }

    public void Process() {
        if(_TryConnect()) {
            _TryRecv();
            _TrySend();
        }
    }

    private Socket _socket;
    private List<byte> _input = new List<byte>();
    private List<byte> _output = new List<byte>();
    private string _host = "";
    private int _port = 0;
}
