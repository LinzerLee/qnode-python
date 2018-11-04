using System.Collections;
using System.Collections.Generic;

public class GameState {
    public enum State {
        Menu,
        Start,
        Running,
        Pause,
        Dancing
    };

    public void Run() {
        if(TestMenu()) {
            _state = State.Running;
            OnRun();
        }
    }

    public void Pause() {
        if (TestRunning()) {
            _state = State.Pause;
            OnPause();
        }
    }

    public void Resume() {
        if (TestPause()) {
            _state = State.Running;
            OnResume();
        }
    }

    public void Dance() {
        if (TestRunning()) {
            _state = State.Dancing;
            OnDance();
        }
    }

    public bool TestPause() {
        return State.Pause == _state;
    }

    public bool TestMenu() {
        return State.Menu == _state;
    }

    public bool TestRunning() {
        return State.Running == _state;
    }

    public bool TestDancing() {
        return State.Dancing == _state;
    }

    // 定义事件委托
    public delegate void StateChangeEventHandler(State state);
    public delegate void RunEventHandler();
    public delegate void PauseEventHandler();
    public delegate void ResumeEventHandler();
    public delegate void DanceEventHandler();
    // 声明事件
    public event StateChangeEventHandler StateChangeEvent;
    public event RunEventHandler RunEvent;
    public event PauseEventHandler PauseEvent;
    public event ResumeEventHandler ResumeEvent;
    public event DanceEventHandler DanceEvent;

    void OnStateChange() {
        if(null != StateChangeEvent)
            StateChangeEvent(_state);
    }

    void OnRun() {
        if (null != RunEvent)
            RunEvent();

        OnStateChange();
    }

    void OnPause() {
        if (null != PauseEvent)
            PauseEvent();

        OnStateChange();
    }

    void OnResume() {
        if (null != ResumeEvent)
            ResumeEvent();

        OnStateChange();
    }

    void OnDance() {
        if (null != DanceEvent)
            DanceEvent();

        OnStateChange();
    }

    public static GameState Instance() {
        if (instance == null) {
            instance = new GameState();
            instance._state = State.Menu;
        }

        return instance;
    }

    private static GameState instance;
    private GameState() { }

    private State _state { get; set; }
}
