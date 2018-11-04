using UnityEngine;
using System.Collections;
using UnityStandardAssets.Characters.FirstPerson;

public class AddBullet : MonoBehaviour {
    // 第一人称控制器
    public FirstPersonController fpc;
    private float _angle = 0.0f;
    // Use this for initialization
    void Start() {

    }

    // Update is called once per frame
    void Update() {
        if (Vector3.Distance(fpc.transform.position, transform.position) < 2) {
            fpc.transform.SendMessage("AddBullet", 100);
            Destroy(this.gameObject);
        }

        _angle += 0.01f;
        if (_angle > 2 * Mathf.PI) {
            _angle -= 2 * Mathf.PI;
        }
    }
}
