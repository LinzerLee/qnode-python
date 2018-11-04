using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public struct Enemy {
    public enum EnemyState {
        Idle,
        Run,
        Attack,
        Dead,
        UnderAttack
    };

    // 定义事件委托
    public delegate void StateChangeEventHandler(EnemyState state);
    public delegate void AttractingEventHandler();
    public delegate void AttackingEventHandler();
    public delegate void IdlingEventHandler();
    public delegate void DeadEventHandler();
    // 声明事件
    public event StateChangeEventHandler StateChangeEvent;
    public event AttractingEventHandler AttractingEvent;
    public event AttackingEventHandler AttackingEvent;
    public event IdlingEventHandler IdlingEvent;
    public event DeadEventHandler DeadEvent;

    // 怪物名字
    public string Name { get; set; }
    // 怪物状态
    public EnemyState State { get; set; }
    // 攻击距离范围
    public int AttackDistance { get; set; }
    // 吸引怪物距离
    public int AttractDistance { get; set; }
    // 攻击伤害范围
    public int MinAttack { get; set; }
    public int MaxAttack { get; set; }
    // 是否被攻击
    public bool IsAttacked { get; private set; }
    // 是否吸引仇恨
    public bool IsAttracting { get; private set; }

    // 激活仇恨
    public void Attracting() {
        State = EnemyState.Run;
        if (!IsAttracting) {
            IsAttracting = true;
            OnAttracting();
        }
    }

    void OnAttracting() {
        if(null != AttractingEvent) {
            AttractingEvent();
        }

        OnStateChange();
    }

    // 发起攻击
    public void Attacking() {
        // 只有激活仇恨后才能发起攻击
        if(IsAttracting) {
            State = EnemyState.Attack;
            OnAttacking();
        }
    }

    void OnAttacking() {
        if (null != AttackingEvent) {
            AttackingEvent();
        }

        OnStateChange();
    }

    public void Idling() {
        IsAttracting = false;
        if(EnemyState.Idle != State) {
            State = EnemyState.Idle;
            OnIdling();
        }
    }

    void OnIdling() {
        if (null != IdlingEvent) {
            IdlingEvent();
        }

        OnStateChange();
    }

    public void Deading() {
        IsAttracting = false;
        IsAttacked = false;
        State = EnemyState.Dead;
        OnDeading();
    }

    void OnDeading() {
        if (null != DeadEvent) {
            DeadEvent();
        }

        OnStateChange();
    }

    void OnStateChange() {
        if (null != StateChangeEvent)
            StateChangeEvent(State);
    }
}
