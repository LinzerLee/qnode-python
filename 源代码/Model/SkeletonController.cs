using UnityEngine;
using System.Collections;

public class SkeletonController : MonoBehaviour {
    //主角
    Transform player;
    // 怪物数据
    Enemy enemy;
    //动画
    Animation anim;
    //寻路
    UnityEngine.AI.NavMeshAgent agent;
    
    private GameData _data = GameData.Instance();
    private bool isDead = false;
    // Use this for initialization
    void Start () {
        enemy.AttackDistance = 4;
        enemy.AttractDistance = 10;
        enemy.MinAttack = 6;
        enemy.MaxAttack = 10;
        enemy.State = Enemy.EnemyState.Idle;

        player = GameObject.Find("FPSController").GetComponent<Transform>();
        anim = GetComponent<Animation>();
        agent = GetComponent<UnityEngine.AI.NavMeshAgent>();
    }

    // Update is called once per frame
    void Update () {
        if(_data.State.TestRunning())
            CheckState();
        
        if (_data.State.TestDancing())
            OnDance();
    }

    //检测怪物状态
    void CheckState() {
        if (Enemy.EnemyState.Dead == enemy.State) {
            enabled = false;
        } else if (Vector3.Distance(player.position, transform.position) <= enemy.AttractDistance &&
            Vector3.Distance(player.position, transform.position) > enemy.AttackDistance) {
            // 激活仇恨
            enemy.Attracting();
        } else if (Vector3.Distance(player.position, transform.position) <= enemy.AttackDistance) {
            // 发起攻击
            enemy.Attacking();
        } else if (enemy.IsAttacked || enemy.IsAttracting) {
            enemy.Attracting();
        } else {
            enemy.Idling();
        }

        switch (enemy.State) {
            case Enemy.EnemyState.Idle:
                anim.Play("idle");
                break;
            case Enemy.EnemyState.Run:
                anim.CrossFade("run", 0.1f, PlayMode.StopAll);
                RunToPlayer();
                break;
            case Enemy.EnemyState.Attack:
                //上一次攻击完了之后才进行下一次攻击
                RunToPlayer();
                if (false == anim.isPlaying) {
                    Attack();
                }
                break;
            case Enemy.EnemyState.Dead:
                agent.destination = transform.position;
                agent.enabled = false;
                anim.Play("die");
                Destroy(gameObject, 1.6f);
                isDead = true;
                break;
            case Enemy.EnemyState.UnderAttack:
                break;
            default:
                Debug.Log("Error State = " + enemy.State);
                break;
        }
    }

    // 攻击
    private void Attack() {
        int attack = Random.Range(enemy.MinAttack, enemy.MaxAttack);
        player.SendMessage("AttackAction", attack);
        anim.Play("attack");
    }

    // 死亡
    void DeadAction() {
        _data.Money += 10;
        enemy.Deading();
        _data.Enemy -= 1;
    }

    void RunToPlayer() {
        Vector3 rotateVector = player.position - transform.position;
        Quaternion newRotation = Quaternion.LookRotation(rotateVector);
        transform.rotation = Quaternion.RotateTowards(transform.rotation, newRotation, Quaternion.Angle(transform.rotation, newRotation));
        agent.destination = player.position;
    }

    void OnDance() {
         if(!isDead && !anim.IsPlaying("dance"))
            anim.Play("dance");
    }
}