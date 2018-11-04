using System;
using System.Collections.Generic;
using System.Text;
using UnityEngine;

public class User {
    public string username = "";
    public string service = "";
}

public class NetworkController : MonoBehaviour {

    private GameData _data = GameData.Instance();
    private ARPCProxy _proxy = new ARPCProxy();
    private Guid _session = Guid.Empty;
    
    // Use this for initialization
    void Start () {
        _proxy.ConnectedEvent += OnConnected;
	}
	
	// Update is called once per frame
	void Update () {
        _proxy.Process();
    }

    // 连接服务器请求动作
    void ConnectAction(User user) {
        string[] addr = user.service.Split(':');
        string ip = addr[0];
        int port = int.Parse(addr[1]);

        _proxy.Run(ip, port);
        _data.Username = user.username;
    }

    // 成功连接到服务器
    void OnConnected() {
        _session = _proxy.Call("Login", ARPCProxy.P("Username", _data.Username));
        _proxy.Commit(_session, OnLoginSuccess);
    }

    // 登陆成功
    void OnLoginSuccess(Dictionary<string, Message> result) {
        _data.Cookie = new Guid(((Message.MString)result["Cookie"]).Value);
        _data.Health = (int)((Message.MLong)result["Health"]).Value;
        _data.Defense = (int)((Message.MLong)result["Defense"]).Value;
        _data.Second = (int)((Message.MLong)result["Second"]).Value;
        _data.Bullet = (int)((Message.MLong)result["Bullet"]).Value;
        _data.Money = (int)((Message.MLong)result["Money"]).Value;
        GameState.Instance().Run();
    }

    // 同步游戏数据
    void SaveGameData() {
        _proxy.Send("SaveGameData", ARPCProxy.P("Health", _data.Health), ARPCProxy.P("Defense", _data.Defense), 
            ARPCProxy.P("Second", _data.Second), ARPCProxy.P("Bullet", _data.Bullet), ARPCProxy.P("Money", _data.Money));
    }
}
