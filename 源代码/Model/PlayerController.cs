using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityStandardAssets.Characters.FirstPerson;

public class PlayerController : MonoBehaviour {
    // 网络控制器
    public GameObject Network;
    // 第一人称控制器
    public FirstPersonController fpc;
    // 受重力影响的子弹
    public Rigidbody BulletModel;
    // 枪模型
    public GameObject Gun;
    // 发射位置
    public Transform FirePoint;

    // 游戏运行时数据
    private GameData _data = GameData.Instance();

    // Use this for initialization
    void Start () {
        fpc.enabled = false;
        _data.State.RunEvent += OnRun;
        _data.State.PauseEvent += OnPause;
        _data.State.ResumeEvent += OnResume;
    }
	
	// Update is called once per frame
	void Update () {
		if(Input.GetKeyUp(KeyCode.Escape)) {
            GameState.Instance().Pause();
        }

        if (!_data.State.TestRunning())
            return;

        Ray ray = Camera.main.ScreenPointToRay(Input.mousePosition);
        if (Input.GetMouseButtonDown(0) && _data.Bullet > 0) {
            -- _data.Bullet;
            Vector3 target = ray.GetPoint(20);
            //实例化子弹
            Rigidbody clone = (Rigidbody)Instantiate(BulletModel, FirePoint.position, FirePoint.rotation);
            //初始化子弹的方向速度
            clone.velocity = (target - FirePoint.position) * 3;
            //播放子弹音频
            Gun.SendMessage("ShootAction");
            RaycastHit hit;
            //如果射线碰到物体的话 1 << 9 打开第九层
            if (Physics.Raycast(ray, out hit, 100, 1 << 9)) {
                //销毁碰撞器
                Destroy(hit.collider);
                hit.transform.gameObject.SendMessage("DeadAction");
            }
        }
        //修改发射起点的朝向
        FirePoint.LookAt(Camera.main.ScreenPointToRay(Input.mousePosition).GetPoint(20));

        if(GameState.Instance().TestRunning()) {
            Network.SendMessage("SaveGameData");
        }
        /*
        if(_data.Money > 1000) {
            _data.State.Dance();
        }
        */

        if(_data.Health <= 0) {
            SceneManager.LoadScene("GameOver");
        }
    }

    void OnRun() {
        fpc.enabled = true;
    }

    void OnPause() {
        fpc.enabled = false;
    }

    void OnResume() {
        fpc.enabled = true;
    }

    // 受到攻击
    public void AttackAction(int attack) {
        _data.Health -= attack;
    }

    public void AddBlood(int value) {
        _data.Health += value;
    }

    public void AddBullet(int value) {
        _data.Bullet += value;
    }
}
