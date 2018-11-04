using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class GUIController : MonoBehaviour {
    public GUISkin skin;
    public string playOrResume;
    public Texture logoTex;
    public GameObject Network;

    private GameData _data = GameData.Instance();
    private User _user = new User();
    // Use this for initialization
    void Start() {
        GameState.Instance().PauseEvent += Enable;
        GameState.Instance().RunEvent += Disable;
        GameState.Instance().ResumeEvent += Disable;
    }

    void OnGUI() {
        string _service = _data.GetAllService()[0];
        GUI.skin = skin;

        GUILayout.BeginArea(new Rect(Screen.width / 2 - 210, Screen.height / 2 - 150, 420, 400));

        GUILayout.BeginHorizontal();
        GUILayout.Label(logoTex);
        GUILayout.EndHorizontal();

        GUILayout.Space(100);

        GUILayout.BeginHorizontal();
        GUILayout.Button(_service, GUILayout.Height(50));
        GUILayout.EndHorizontal();

        if (_data.State.TestMenu()) {
            GUILayout.BeginHorizontal();
            _user.username = GUILayout.TextField("Linzer", GUILayout.Height(50));
            GUILayout.EndHorizontal();
        }

        GUILayout.BeginHorizontal();
        if (GUILayout.Button(playOrResume, GUILayout.Height(50))) {
            if ("RESUME" == playOrResume)
                GameState.Instance().Resume();
            else {
                // 请求连接服务器
                _user.service = _data.SelectService(_service);
                Network.SendMessage("ConnectAction", _user);
            }
        }
        GUILayout.EndHorizontal();

        GUILayout.EndArea();
    }

    void Enable() {
        playOrResume = "RESUME";
        enabled = true;
    }

    void Disable() {
        enabled = false;
    }
}


