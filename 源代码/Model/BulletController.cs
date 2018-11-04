using UnityEngine;
using System.Collections;

public class BulletController : MonoBehaviour {

    public float TimeDelay;

    void OnCollisionEnter(Collision collisionInfo)
    {
        Destroy(this.gameObject);
    }

    // Use this for initialization
    void Start () {
        // TimeDelay秒后销毁某个gameObject
        Destroy(this.gameObject, TimeDelay);
    }
	
	// Update is called once per frame
	void Update () {

    }
}
