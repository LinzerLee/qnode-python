using System;
using System.Collections;
using System.Collections.Generic;
using System.Net.Sockets;
using System.Text;
using UnityEngine;

// 异步RPC代理
public class ARPCProxy {
    private class RPCCall : Message.MDictionary<Message.MString, Message> {
        public static new Guid GUID = new Guid("8e6bfc8f-640a-402b-abbe-7cf9fcf873b9");
        static RPCCall() {
            Register(GUID, typeof(RPCCall));
        }

        public string Method {
            get {
                if(ContainsKey("Method"))
                    return ((MString)this["Method"]).Value;

                return null;
            }

            set {
                Add("Method", Convert(value));
            }
        }

        public string Session {
            get {
                if (ContainsKey("Session"))
                    return ((MString)this["Session"]).Value;

                return null;
            }

            set {
                Add("Session", Convert(value));
            }
        }

        public MDictionary<MString, Message> Params {
            get {
                if (!ContainsKey("Params") || null == this["Params"]) {
                    this["Params"] = new MDictionary<MString, Message>();
                }

                return (MDictionary<MString, Message>)this["Params"];
            }
        }

        public override string ToString() {
            string result = Method + " ( ";
            foreach (var p in Params) {
                result += string.Format("{0} = {1}, ", p.Key, p.Value);
            }
            result +=  Session + " )";
            return result;
        }
    }

    private class RPCResult : Message.MDictionary<Message.MString, Message> {
        public static new Guid GUID = new Guid("c7915151-3c57-4507-abc9-7e1293ba134d");
        static RPCResult() {
            Register(GUID, typeof(RPCResult));
        }

        public string Method {
            get {
                if (ContainsKey("Method"))
                    return ((MString)this["Method"]).Value;

                return null;
            }

            set {
                Add("Method", Convert(value));
            }
        }

        public string Session {
            get {
                if (ContainsKey("Session"))
                    return ((MString)this["Session"]).Value;

                return null;
            }

            set {
                Add("Session", Convert(value));
            }
        }

        // ErrorCode : RPC系统代码
        // -1 : 尚未返回
        //  0 : 调用成功
        //  1 : 无效参数
        //  2 : 处理超时
        //  3 : 延迟处理
        public int ErrorCode {
            get {
                if (ContainsKey("ErrorCode"))
                    return ((MInt)this["ErrorCode"]).Value;

                return -1;
            }

            set {
                Add("ErrorCode", Convert(value));
            }
        }

        public MDictionary<MString, Message> Results {
            get {
                if (!ContainsKey("Results") || null == this["Results"]) {
                    this["Results"] = new MDictionary<MString, Message>();
                }

                return (MDictionary<MString, Message>)this["Results"];
            }
        }

        public override string ToString() {
            string result = Method + " ( ";
            foreach (var r in Results) {
                result += string.Format("{0} = {1}, ", r.Key, r.Value);
            }
            result += Session + " ) Return";
            return result;
        }

        public override void FromDictionary(MDictionary<MString, Message> mobj) {
            foreach (var kv in mobj) {
                if (kv.Key.Value == "Method") {
                    Method = ((MString)kv.Value).Value;
                } else if (kv.Key.Value == "Session") {
                    Session = ((MString)kv.Value).Value;
                } else if (kv.Key.Value == "ErrorCode") {
                    ErrorCode = (int)((MLong)kv.Value).Value;
                } else if (kv.Key.Value == "Results" && kv.Value is MDictionary<MString, Message>) {
                    MDictionary<MString, Message> dict = (MDictionary<MString, Message>)kv.Value;
                    foreach(var d in dict) {
                        if (d.Value is MDictionary<MString, Message>) {
                            Results.Add(d.Key, TryParseToObject((MDictionary<MString, Message>)d.Value));
                        } else {
                            Results.Add(d.Key, d.Value);
                        }
                    }
                } else if (kv.Key.Value == "Type") {
                    // 忽略Type
                } else {
                    throw new Exception("RPCResult格式不正确 " + kv.Key + " : " + mobj.ToJson());
                }
            }
        }
    }

    private Dictionary<Guid, RPCResult> _future = new Dictionary<Guid, RPCResult>();
    private NetStream _stream;
    private Dictionary<Guid, FutureEventHandler> _callback = new Dictionary<Guid, FutureEventHandler>();
    // 定义事件委托
    public delegate void ConnectedEventHandler();
    public delegate void DisconnectedEventHandler();
    public delegate void RetryEventHandler(float waitForSecond);
    public delegate void FutureEventHandler(Dictionary<string, Message> result);
    // 声明事件
    public event ConnectedEventHandler ConnectedEvent;
    public event DisconnectedEventHandler DisconnectedEvent;
    public event RetryEventHandler RetryEvent;

    static ARPCProxy() {
        Guid guid = RPCCall.GUID;
        guid = RPCResult.GUID;
    }

    public ARPCProxy() {
        _stream = null;
    }

    public ARPCProxy(string host, int port) {
        Run(host, port);
    }

    public void Run(string host, int port) {
        if(null != _stream) {
            throw new Exception("NetStream已经配置完毕");
        }

        _stream = new NetStream(host, port);
        _stream.ConnectedEvent += OnConnected;
        _stream.DisconnectedEvent += OnDisconnected;
        _stream.RetryEvent += OnRetryConnect;
    }

    // 异步结果获取
    public int Future(Guid session, out Dictionary<string, Message> result) {
        if (_future.ContainsKey(session)) {
            if(null != _future[session]) {
                int errcode = _future[session].ErrorCode;
                result = new Dictionary<string, Message>();
                foreach(var r in _future[session].Results) {
                    result[r.Key.Value] = r.Value;
                }
                _future.Remove(session);

                return errcode;
            }
        }

        result = null;
        return -1;
    }

    public static KeyValuePair<Message.MString, Message> P(string key, object value) {
        return new KeyValuePair<Message.MString, Message>(new Message.MString(key), Message.Convert(value));
    }

    public void Send(string method, params KeyValuePair<Message.MString, Message>[] param) {
        Call(method, param);
    }

    public Guid Call(string method, params KeyValuePair<Message.MString, Message>[] param) {
        if(null == _stream) {
            throw new SocketException();
        }

        RPCCall call = new RPCCall();
        call.Method = method;
        call.Session = Guid.NewGuid().ToString();
        foreach (var p in param) {
            call.Params.Add(p);
        }
        _stream.Send(call);

        return new Guid(call.Session);
    }

    public void Commit(Guid session, FutureEventHandler future) {
        _callback.Remove(session);
        Dictionary<string, Message> rr = null;
        if (-1 != Future(session, out rr)) {
            future(rr);
        } else {
            _callback[session] = future;
        }
    }

    public void Process() {
        if (null == _stream)
            return;

        _stream.Process();

        List<Message> results = _stream.Receive();
        if(null != results) {
            foreach (var r in results) {
                if(r is RPCResult) {
                    RPCResult result = (RPCResult)r;
                    Guid session = new Guid(result.Session);
                    _future[session] = result;
                    if (_callback.ContainsKey(session)) {
                        Dictionary<string, Message> rr = null;
                        if(-1 != Future(session, out rr)) {
                            _callback[session](rr);
                            _future.Remove(session);
                        } else {
                            throw new Exception("<Bug>");
                        }
                    }
                }
            }
        }
    }

    // 连接成功
    void OnConnected() {
        if (null != ConnectedEvent)
            ConnectedEvent();
    }

    // 连接断开
    void OnDisconnected() {
        if (null != DisconnectedEvent)
            DisconnectedEvent();
    }

    // 重连
    void OnRetryConnect(float waitForSecond) {
        if (null != RetryEvent)
            RetryEvent(waitForSecond);
    }
}
