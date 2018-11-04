using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class GameController : MonoBehaviour {
    public Transform skeleton;
    public Transform player;
    public Transform Enemys;

    private GameData _data = GameData.Instance();

	// Use this for initialization
	void Start () {
        GameState.Instance().DanceEvent += OnDance;
        // Spawn Enemy
        for (int i = 0; i < 10; ++i) {
            Instantiate(skeleton, new Vector3(skeleton.position.x + i * 2, skeleton.position.y, skeleton.position.z + i * 2), Quaternion.identity).parent = Enemys;
            _data.Enemy += 1;
        }
    }
	
	// Update is called once per frame
	void Update () {
		if(_data.Enemy < 10) {
            for (int i = 0; i < 5; ++i) {
                Instantiate(skeleton, new Vector3(skeleton.position.x + i * 2, skeleton.position.y, skeleton.position.z + i * 2), Quaternion.identity).parent = Enemys;
                _data.Enemy += 1;
            }
        }
	}
    
    void OnDance() {
        AudioSource audio = GetComponent<AudioSource>();
        audio.Play();
    }
}
