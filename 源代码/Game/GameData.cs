using System;
using System.Collections.Generic;
using UnityEngine;

// 游戏运行时数据
public class GameData {
    public string Username = "";
    public Guid Cookie = Guid.Empty;

    public GameState State {
        get {
            return GameState.Instance();
        }
    }

    private GameData() {
        _services["魔域求生 - PC服"] = "127.0.0.1:7777";
    }

    public bool TestLogin() {
        return !Cookie.Equals(Guid.Empty);
    }

    private Dictionary<string, string> _services = new Dictionary<string, string> ();
    public string[] GetAllService() {
        List<string> services = new List<string>();

        foreach(var s in _services.Keys) {
            services.Add(s);
        }
        return services.ToArray();
    }

    public string SelectService(string name) {
        if (_services.ContainsKey(name)) {
            return _services[name];
        }

        return ":0";
    }

    public void SelectService(string name, out string ip, out int port) {
        string[] addr = SelectService(name).Split(':');
        ip = addr[0];
        port = int.Parse(addr[1]);
    }

    private int _health = 0;
    public int Health {
        get { return _health; }
        set {
            if (value > 100)
                value = 100;

            if (value < 0)
                value = 0;

            _health = value;
        }
    }

    private int _defense = 0;
    public int Defense {
        get { return _defense; }
        set {
            if (value > 100)
                value = 100;

            if (value < 0)
                value = 0;

            _defense = value;
        }
    }

    private int _second = 0;
    public int Second {
        get { return _second; }
        set {
            if (value < 0)
                value = 0;

            _second = value;
        }
    }

    private int _bullet = 0;
    public int Bullet {
        get { return _bullet; }
        set {
            if (value < 0)
                value = 0;

            _bullet = value;
        }
    }

    private int _money = 0;
    public int Money {
        get { return _money; }
        set {
            if (value < 0)
                value = 0;

            _money = value;
        }
    }

    private int _enemy = 0;
    public int Enemy {
        get { return _enemy; }
        set {
            if (value < 0)
                value = 0;

            _enemy = value;
        }
    }

    public Color HealthColor(Color normal, Color warning, Color dangerous) {
        if (Health >= 50)
            return normal;

        if (Health <= 30)
            return dangerous;

        return warning;
    }

    public Color DefenseColor(Color normal, Color warning, Color dangerous) {
        if (Defense >= 50)
            return normal;

        if (Defense <= 30)
            return dangerous;

        return warning;
    }

    public Color SecondColor(Color normal, Color warning, Color dangerous) {
        if (Second >= 120)
            return normal;

        if (Second <= 60)
            return dangerous;

        return warning;
    }

    public Color BulletColor(Color normal, Color warning, Color dangerous) {
        if (Bullet >= 30)
            return normal;

        if (Bullet <= 10)
            return dangerous;

        return warning;
    }

    
    // public LinkedList<GameObject>

    public static GameData Instance() {
        if (instance == null) {
            instance = new GameData();
        }

        return instance;
    }

    private static GameData instance;
}
