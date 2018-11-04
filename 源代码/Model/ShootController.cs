using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class ShootController : MonoBehaviour {

	// Use this for initialization
	void Start () {
		
	}
	
	// Update is called once per frame
	void Update () {
		
	}

    void ShootAction() {
        AudioSource audio = GetComponent<AudioSource>();
        audio.Play();
    }
}
