using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class GameOver : MonoBehaviour {

    public Texture2D GameOverTex;

    // Use this for initialization
    void Start () {
		
	}

    // Update is called once per frame
    void Update() {
        if (Input.GetKeyDown(KeyCode.Escape)) {
            Application.Quit();
        }
    }

    void OnGUI() {
        GUI.DrawTexture(new Rect(0, 0, Screen.width, Screen.height), GameOverTex);
    }
}
