using System;
using System.Collections.Generic;
using System.Text;
using UnityEngine;

class RichTextString {
    public Color color { get; set; }
    public int size { get; set; }
    public bool i { get; set; }
    public bool b { get; set; }
    public string Text { get; set; }

    public RichTextString() {
        Text = "";
        color = Color.white;
    }

    public RichTextString(RichTextString rts) {
        Text = rts;
        color = Color.white;
    }

    public override string ToString() {
        string result = Text;
        
        if (Color.white != color) {
            int r = (int)(color.r * 255.0f);
            int g = (int)(color.g * 255.0f);
            int b = (int)(color.b * 255.0f);
            int a = (int)(color.a * 255.0f);
            result = string.Format("<color=#{0:X2}{1:X2}{2:X2}{3:X2}>{4}</color>", r, g, b, a, result);
        }
        
        if (i) {
            result = string.Format("<i>{0}</i>", result);
        }

        if (b) {
            result = string.Format("<b>{0}</b>", result);
        }

        return result;
    }

    public static implicit operator string(RichTextString rts) {
        return rts.ToString();
    }
}
