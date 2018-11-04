using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class PanelController : MonoBehaviour {
    public GUISkin Skin;
    public Texture HealthTex;
    public Texture DefenseTex;
    public Texture TimeTex;
    public Texture BulletTex;
    public Texture MoneyTex;
    // 准星贴图
    public Texture2D FrontSightTex;
    // 血量背景贴图
    public Texture2D BloodBgTex;
    // 血量贴图
    public Texture2D BloodTex;
    // 健康告警贴图
    public Texture2D HealthWarnTex;
    // 全屏红色透明度
    public float HealthAlpha;
    public Color NormalColor;
    public Color WarningColor;
    public Color DangerousColor;

    private GameData _data = GameData.Instance();
    // Use this for initialization
    void Start () {
        Disable();
        _data.State.RunEvent += Enable;
        _data.State.ResumeEvent += Enable;
        _data.State.PauseEvent += Disable;
    }

    void OnGUI() {
        // 准星贴图
        Rect rect = new Rect(Input.mousePosition.x - (FrontSightTex.width / 2),
                             Screen.height - Input.mousePosition.y - (FrontSightTex.height / 2), 
                             FrontSightTex.width, 
                             FrontSightTex.height);
        GUI.DrawTexture(rect, FrontSightTex);
        // 总血条贴图
        GUI.DrawTexture(new Rect(0, 0, BloodBgTex.width, BloodBgTex.height), BloodBgTex);
        GUI.DrawTexture(new Rect(0, 0, BloodTex.width * (_data.Health * 0.01f), BloodTex.height), BloodTex);
        // 血量全屏贴图
        Color alpha = GUI.color;
        HealthAlpha = (100.0f - _data.Health) / 120.0f;
        if (HealthAlpha < 0.42) {
            HealthAlpha = 0;
        }
        alpha.a = HealthAlpha;
        GUI.color = alpha;
        GUI.DrawTexture(new Rect(0, 0, Screen.width, Screen.height), HealthWarnTex);

        alpha.a = 1.0f;
        GUI.color = alpha;
        GUI.skin = Skin;
        RichTextString rts = new RichTextString();
        GUILayout.BeginArea(new Rect(0, 0, Screen.width, Screen.height));

        GUILayout.FlexibleSpace();

        GUILayout.BeginHorizontal();
        GUILayout.FlexibleSpace();
        GUILayout.Label(HealthTex);
        rts.color = _data.HealthColor(NormalColor, WarningColor, DangerousColor);
        rts.Text = _data.Health.ToString();
        GUILayout.Label(rts);
        GUILayout.FlexibleSpace();
        GUILayout.Label(DefenseTex);
        rts.color = _data.DefenseColor(NormalColor, WarningColor, DangerousColor);
        rts.Text = _data.Defense.ToString();
        GUILayout.Label(rts);
        GUILayout.FlexibleSpace();
        GUILayout.Label(TimeTex);
        rts.color = _data.SecondColor(NormalColor, WarningColor, DangerousColor);
        rts.Text = string.Format("{0:D}:{1:D2}", _data.Second / 60, _data.Second % 60);
        GUILayout.Label(rts);
        GUILayout.FlexibleSpace();
        GUILayout.Label(BulletTex);
        rts.color = _data.BulletColor(NormalColor, WarningColor, DangerousColor);
        rts.Text = _data.Bullet.ToString();
        GUILayout.Label(rts);
        GUILayout.FlexibleSpace();
        GUILayout.Label(MoneyTex);
        rts.color = NormalColor;
        rts.Text = _data.Money.ToString();
        GUILayout.Label(rts);
        GUILayout.FlexibleSpace();
        GUILayout.EndHorizontal();

        GUILayout.EndArea();
    }

    void Enable() {
        enabled = true;
    }

    void Disable() {
        enabled = false;
    }
}
