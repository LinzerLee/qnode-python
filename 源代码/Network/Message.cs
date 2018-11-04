using System;
using System.Collections;
using System.Collections.Generic;
using System.Net;
using System.Runtime.Serialization;
using System.Text;
using UnityEngine;

public abstract class Message {
    public static Guid GUID = new Guid("dd2beee7-bc33-4940-91d3-90142c85f2a5");
    static Message() {
        Register(GUID, typeof(Message));
        Guid guid = MByte.GUID;
        guid = MChar.GUID;
        guid = MShort.GUID;
        guid = MUShort.GUID;
        guid = MInt.GUID;
        guid = MUInt.GUID;
        guid = MLong.GUID;
        guid = MULong.GUID;
        guid = MDouble.GUID;
        guid = MString.GUID;
        guid = MList<Message>.GUID;
        guid = MDictionary<MString, Message>.GUID;
    }

    private static Dictionary<Guid, Type> _types = new Dictionary<Guid, Type>();
    public static void Register(Guid guid, Type type) {
        _types[guid] = type;
    }

    public static void Unregister(Guid guid) {
        _types.Remove(guid);
    }

    // 格式不完整的包也可能检测通过
    public static bool CheckFormat(List<byte> bytes, out List<byte> data) {
        /*
         * TLV Protocol
         * Magic(4B):      1A2B3C4D
         * Checksum(2B):
         * Type(2B):       raw          1
         *                 json         2
         *                 xml          3
         *                 protobuf     4
         * Length(4B):     size
         * Value(size)
         */
        data = null;
        // 不够包的最小长度默认通过检测
        if (bytes.Count < 12) {
            return true;
        }

        byte[] head = bytes.GetRange(0, 12).ToArray();
        uint magic = (uint)IPAddress.NetworkToHostOrder((int)BitConverter.ToUInt32(head, 0));
        ushort checksum = (ushort)IPAddress.NetworkToHostOrder((short)BitConverter.ToUInt32(head, 4));
        ushort type = (ushort)IPAddress.NetworkToHostOrder((short)BitConverter.ToUInt32(head, 6));
        int size = IPAddress.NetworkToHostOrder((int)BitConverter.ToUInt32(head, 8));
        
        // 检测魔术数字和协议类型
        if (0x1A2B3C4D != magic || type != 1)
            return false;

        // 完整包就检测CheckSum
        if(bytes.Count >= size) {
            List<byte> d = bytes.GetRange(12, size - 12);
            if(checksum != CheckSum(d.ToArray())) {
                return false;
            } else {
                data = d;
                bytes.RemoveRange(0, size);
            }
        }

        return true;
    }
    // 检测包的完整性
    public static bool CheckComplete(List<byte> bytes, out List<byte> data) {
        data = null;
        if (CheckFormat(bytes, out data)) {
            if(null != data) {
                return true;
            }
        }

        bytes.RemoveAt(0);
        return false;
    }
    // 获取一个包
    public static string GetPackage(List<byte> bytes) {
        List<byte> data = null;
        if (CheckComplete(bytes, out data)) {
            return Encoding.ASCII.GetString(data.ToArray());
        }

        return null;
    }

    public static Message ParserJson(string json) {
        json = json.Trim();
        if (json.StartsWith("{") && json.EndsWith("}")) {
            // 对象或字典(先转化为字典,再通过Type转化为对象)
            MDictionary<MString, Message> obj = new MDictionary<MString, Message>();
            int match = 0;
            int last = 0;
            int index;
            string key, value, elm;
            json = json.Substring(1, json.Length - 2);
            for (int i = 0; i < json.Length; ++i) {
                if (json[i] == '{' || json[i] == '[')
                    ++ match;
                else if (json[i] == '}' || json[i] == ']')
                    -- match;
                else if (match == 0 && json[i] == ',') {
                    elm = json.Substring(last, i - last);
                    index = elm.IndexOf(':');
                    if(-1 == index) {
                        throw new Exception("数据格式错误");
                    }

                    key = elm.Substring(0, index).Trim().Trim('\"');
                    value = elm.Substring(index + 1);
                    obj.Add(new MString(key), ParserJson(value));
                    last = i + 1;
                }
            }
            elm = json.Substring(last);
            index = elm.IndexOf(':');
            key = elm.Substring(0, index).Trim().Trim('\"');
            value = elm.Substring(index + 1);
            obj.Add(new MString(key), ParserJson(value));
            return obj;
        } else if (json.StartsWith("[") && json.EndsWith("]")) {
            // 数组
            MList<Message> list = new MList<Message>();
            int match = 0;
            int last = 0;
            json = json.Substring(1, json.Length - 2);
            for(int i = 0; i < json.Length; ++ i) {
                if (json[i] == '{' || json[i] == '[')
                    ++ match;
                else if (json[i] == '}' || json[i] == ']')
                    -- match;
                else if (match == 0 && json[i] == ',') {
                    list.Add(ParserJson(json.Substring(last, i - last)));
                    last = i + 1;
                }
            }
            list.Add(ParserJson(json.Substring(last)));
            return list;
        } else if (json.StartsWith("\"") && json.EndsWith("\"")) {
            // 字符串
            return new MString(json.Trim('\"'));
        } else if (json.StartsWith("\'") && json.EndsWith("\'")) {
            // 字符
            return new MChar(json[1]);
        } else if(-1 != json.IndexOf('.')) {
            // 浮点数
            double num;
            double.TryParse(json, out num);
            return new MDouble(num);
        } else {
            // 整数
            long num;
            long.TryParse(json, out num);
            return new MLong(num);
        }
    }

    public static Message TryParseToObject(MDictionary<MString, Message> obj) {
        if (obj.ContainsKey("Type")) {
            Guid guid = new Guid(((MString)obj["Type"]).Value);
            if (_types.ContainsKey(guid)) {
                Message mobj = (Message)Activator.CreateInstance(_types[guid]);
                mobj.FromDictionary(obj);

                return mobj;
            }
        }

        return obj;
    }

    // 尽可能多的反序列化出包
    public static List<Message> Unserialize(List<byte> bytes) {
        List<Message> packs = new List<Message>();
        while (bytes.Count > 0) {
            string json = GetPackage(bytes);
            // Debug.Log(json);
            if(null != json) {
                Message msg = ParserJson(json);
                if (msg is MDictionary<MString, Message>) {
                    packs.Add(TryParseToObject((MDictionary<MString, Message>)msg));
                } else {
                    throw new Exception("数据格式错误");
                }
            }
        }
        return packs;
    }

    public virtual void FromDictionary(MDictionary<MString, Message> mobj) {
        throw new NotImplementedException();
    }

    public virtual void FromJson(string json) {
        throw new NotImplementedException();
    }

    public virtual string ToJson() {
        throw new NotImplementedException();
    }

    public static ushort CheckSum(byte[] data) {
        uint checksum = 0;
        int index = 0;
        while (index + 2 < data.Length) {
            checksum += (ushort)IPAddress.NetworkToHostOrder((short)BitConverter.ToUInt16(data, index));
            index += 2;
        }
        index = data.Length - index;
        if (1 == index) {
            checksum += (ushort)data[data.Length - 1];
        }

        checksum = (checksum >> 16) + (checksum & 0xffff);
        checksum = checksum + (checksum >> 16);
        
        return (ushort)(~checksum & 0xffff);
    }

    public virtual byte[] Serialize() {
        /*
         * TLV Protocol
         * Magic(4B):      1A2B3C4D
         * Checksum(2B):
         * Type(2B):       raw          1
         *                 json         2
         *                 xml          3
         *                 protobuf     4
         * Length(4B):     size
         * Value(size)
         */
        List<byte> bytes = new List<byte>();
        byte[] content = Encoding.ASCII.GetBytes(ToJson());
        bytes.AddRange(BitConverter.GetBytes(IPAddress.HostToNetworkOrder(0x1A2B3C4D)));
        bytes.AddRange(BitConverter.GetBytes(IPAddress.HostToNetworkOrder((short)CheckSum(content))));
        bytes.AddRange(BitConverter.GetBytes(IPAddress.HostToNetworkOrder((short)1)));
        bytes.AddRange(BitConverter.GetBytes(IPAddress.HostToNetworkOrder(content.Length + 12)));
        bytes.AddRange(content);
        return bytes.ToArray();
    }

    // Basic Data Type
    public class MByte : Message {
        public static new Guid GUID = new Guid("1d6ef338-c53a-42b5-9c7d-cf31b3034ce2");
        static MByte() {
            Register(GUID, typeof(MByte));
        }

        public MByte() { }

        public MByte(byte value) {
            Value = value;
        }

        public byte Value;

        public override string ToString() {
            return Value.ToString();
        }

        public override string ToJson() {
            return string.Format("{0}", Value);
        }

        public override void FromDictionary(MDictionary<MString, Message> mobj) {
            Value = ((MByte)mobj["Value"]).Value;
        }
    }

    public class MChar : Message {
        public static new Guid GUID = new Guid("617eee57-75bb-45bd-8140-3fae0a15306d");
        static MChar() {
            Register(GUID, typeof(MChar));
        }

        public MChar() { }

        public MChar(char value) {
            Value = value;
        }

        public char Value;

        public override string ToString() {
            return Value.ToString();
        }

        public override string ToJson() {
            return string.Format("\'{0}\'", Value);
        }

        public override void FromDictionary(MDictionary<MString, Message> mobj) {
            Value = ((MChar)mobj["Value"]).Value;
        }
    }

    public class MShort : Message {
        public static new Guid GUID = new Guid("14fb2032-f550-4884-b155-1d1821242e8c");
        static MShort() {
            Register(GUID, typeof(MShort));
        }

        public MShort() { }

        public MShort(short value) {
            Value = value;
        }

        public short Value;

        public override string ToString() {
            return Value.ToString();
        }

        public override string ToJson() {
            return string.Format("{0}", Value);
        }

        public override void FromDictionary(MDictionary<MString, Message> mobj) {
            Value = ((MShort)mobj["Value"]).Value;
        }
    }

    public class MUShort : Message {
        public static new Guid GUID = new Guid("a84069d1-abc1-4a16-b7b7-080189275c50");
        static MUShort() {
            Register(GUID, typeof(MUShort));
        }

        public MUShort() { }

        public MUShort(ushort value) {
            Value = value;
        }

        public ushort Value;

        public override string ToString() {
            return Value.ToString();
        }

        public override string ToJson() {
            return string.Format("{0}", Value);
        }

        public override void FromDictionary(MDictionary<MString, Message> mobj) {
            Value = ((MUShort)mobj["Value"]).Value;
        }
    }

    public class MInt : Message {
        public static new Guid GUID = new Guid("52e05c9f-0a2e-4369-9d89-80834f49153e");
        static MInt() {
            Register(GUID, typeof(MInt));
        }

        public MInt() { }

        public MInt(int value) {
            Value = value;
        }

        public int Value;

        public override string ToString() {
            return Value.ToString();
        }

        public override string ToJson() {
            return string.Format("{0}", Value);
        }

        public override void FromDictionary(MDictionary<MString, Message> mobj) {
            Value = ((MInt)mobj["Value"]).Value;
        }
    }

    public class MUInt : Message {
        public static new Guid GUID = new Guid("15df8793-47f7-462b-b8f9-8da5f308344d");
        static MUInt() {
            Register(GUID, typeof(MUInt));
        }

        public MUInt() { }

        public MUInt(uint value) {
            Value = value;
        }

        public uint Value;

        public override string ToString() {
            return Value.ToString();
        }

        public override string ToJson() {
            return string.Format("{0}", Value);
        }

        public override void FromDictionary(MDictionary<MString, Message> mobj) {
            Value = ((MUInt)mobj["Value"]).Value;
        }
    }

    public class MLong : Message {
        public static new Guid GUID = new Guid("38d7d249-6104-4407-9a38-5bde09e26581");
        static MLong() {
            Register(GUID, typeof(MLong));
        }

        public MLong() { }

        public MLong(long value) {
            Value = value;
        }

        public long Value;

        public override string ToString() {
            return Value.ToString();
        }

        public override string ToJson() {
            return string.Format("{0}", Value);
        }

        public override void FromDictionary(MDictionary<MString, Message> mobj) {
            Value = ((MLong)mobj["Value"]).Value;
        }
    }

    public class MULong : Message {
        public static new Guid GUID = new Guid("91c3857a-203b-4df2-91de-8bdf800b8559");
        static MULong() {
            Register(GUID, typeof(MULong));
        }

        public MULong() { }

        public MULong(ulong value) {
            Value = value;
        }

        public ulong Value;

        public override string ToString() {
            return Value.ToString();
        }

        public override string ToJson() {
            return string.Format("{0}", Value);
        }

        public override void FromDictionary(MDictionary<MString, Message> mobj) {
            Value = ((MULong)mobj["Value"]).Value;
        }
    }

    public class MFloat : Message {
        public static new Guid GUID = new Guid("9dbec5ab-5ec1-4458-8a33-511f20d7aa53");
        static MFloat() {
            Register(GUID, typeof(MFloat));
        }

        public MFloat() { }

        public MFloat(float value) {
            Value = value;
        }

        public float Value;

        public override string ToString() {
            return Value.ToString();
        }

        public override string ToJson() {
            return string.Format("{0}", Value);
        }

        public override void FromDictionary(MDictionary<MString, Message> mobj) {
            Value = ((MFloat)mobj["Value"]).Value;
        }
    }

    public class MDouble : Message {
        public static new Guid GUID = new Guid("ba3b07cf-af92-4754-a663-f385c12295fb");
        static MDouble() {
            Register(GUID, typeof(MDouble));
        }

        public MDouble() { }

        public MDouble(double value) {
            Value = value;
        }

        public double Value;

        public override string ToString() {
            return Value.ToString();
        }

        public override string ToJson() {
            return string.Format("{0}", Value);
        }

        public override void FromDictionary(MDictionary<MString, Message> mobj) {
            Value = ((MDouble)mobj["Value"]).Value;
        }
    }

    public class MString : Message {
        public static new Guid GUID = new Guid("635519ce-6fa8-4ae2-86bd-fe402d211d28");
        static MString() {
            Register(GUID, typeof(MString));
        }

        public MString() { }

        public MString(string value) {
            Value = value;
        }

        public string Value;

        public override string ToString() {
            return Value;
        }

        public override string ToJson() {
            return string.Format("\"{0}\"", Value);
        }

        public override bool Equals(object obj) {
            return Value.Equals(obj.ToString());
        }

        public override int GetHashCode() {
            return Value.GetHashCode();
        }

        public override void FromDictionary(MDictionary<MString, Message> mobj) {
            Value = ((MString)mobj["Value"]).Value;
        }
    }

    public class MList<T> : Message, IList where T : Message {
        public static new Guid GUID = new Guid("059ebb7c-6d8d-4081-92c4-f5d4bdfcd724");
        static MList() {
            Register(GUID, typeof(MList<T>));
        }

        public MList() {
            Value = new List<T>();
        }

        public MList(List<T> value) {
            Value = value;
        }

        public List<T> Value;

        public override string ToString() {
            string result = "[";

            for (int i = 0; i < Value.Count; ++i) {
                result += Value[i].ToString();
                if (i != Value.Count - 1) {
                     result += ",";
                }
            }
            result += "]";
            return result;
        }

        public override string ToJson() {
            string result = "[";

            for (int i = 0; i < Value.Count; ++i) {
                result += Value[i].ToJson();
                if (i != Value.Count - 1) {
                    result += ",";
                }
            }
            result += "]";
            return result;
        }

        public override void FromDictionary(MDictionary<MString, Message> mobj) {
            Value = ((MList<T>)mobj["Value"]).Value;
        }

        public bool IsReadOnly {
            get {
                return ((IList)Value).IsReadOnly;
            }
        }

        public bool IsFixedSize {
            get {
                return ((IList)Value).IsFixedSize;
            }
        }

        public int Count {
            get {
                return ((IList)Value).Count;
            }
        }

        public object SyncRoot {
            get {
                return ((IList)Value).SyncRoot;
            }
        }

        public bool IsSynchronized {
            get {
                return ((IList)Value).IsSynchronized;
            }
        }

        public object this[int index] {
            get {
                return ((IList)Value)[index];
            }

            set {
                ((IList)Value)[index] = value;
            }
        }

        public int Add(object value) {
            return ((IList)Value).Add(value);
        }

        public bool Contains(object value) {
            return ((IList)Value).Contains(value);
        }

        public void Clear() {
            ((IList)Value).Clear();
        }

        public int IndexOf(object value) {
            return ((IList)Value).IndexOf(value);
        }

        public void Insert(int index, object value) {
            ((IList)Value).Insert(index, value);
        }

        public void Remove(object value) {
            ((IList)Value).Remove(value);
        }

        public void RemoveAt(int index) {
            ((IList)Value).RemoveAt(index);
        }

        public void CopyTo(Array array, int index) {
            ((IList)Value).CopyTo(array, index);
        }

        public IEnumerator GetEnumerator() {
            return ((IList)Value).GetEnumerator();
        }
    }

    public class MDictionary<TKey, TValue> : Message, IDictionary<MString, TValue> 
        where TValue : Message {
        public static new Guid GUID = new Guid("bdfc3d03-8c35-45f0-9000-99abde6bf300");
        static MDictionary() {
            Register(GUID, typeof(Dictionary<MString, TValue>));
        }

        public MDictionary() {
            Value = new Dictionary<MString, TValue>();
        }

        public MDictionary(Dictionary<MString, TValue> value) {
            Value = value;
        }

        public Dictionary<MString, TValue> Value;

        public override string ToString() {
            string result = "{";
            bool first = true;
            foreach (var value in Value) {
                if (!first) {
                    result += ", ";
                } else {
                    first = false;
                }
                MString key = (MString)value.Key;
                result += string.Format("{0} : {1}", value.Key.ToString(), value.Value.ToString());
            }
            result += "}";

            return result;
        }

        public override string ToJson() {
            string result = "{";
            bool first = true;
            foreach(var value in Value) {
                if(!first) {
                    result += ", ";
                } else {
                    first = false;
                }
                MString key = (MString)value.Key;
                result += string.Format("{0} : {1}", value.Key.ToJson(), value.Value.ToJson());
            }
            result += "}";

            return result;
        }

        public TValue this[MString key] {
            get {
                return ((IDictionary<MString, TValue>)Value)[key];
            }

            set {
                ((IDictionary<MString, TValue>)Value)[key] = value;
            }
        }

        public TValue this[string key] {
            get {
                return this[new MString(key)];
            }

            set {
                this[new MString(key)] = value;
            }
        }

        public int Count {
            get {
                return ((IDictionary<MString, TValue>)Value).Count;
            }
        }

        public bool IsReadOnly {
            get {
                return ((IDictionary<MString, TValue>)Value).IsReadOnly;
            }
        }

        public ICollection<MString> Keys {
            get {
                return ((IDictionary<MString, TValue>)Value).Keys;
            }
        }

        public ICollection<TValue> Values {
            get {
                return ((IDictionary<MString, TValue>)Value).Values;
            }
        }

        public void Add(KeyValuePair<MString, TValue> item) {
            ((IDictionary<MString, TValue>)Value).Add(item);
        }

        public void Add(string key, TValue value) {
            Add(new MString(key), value);
        }

        public void Add(MString key, TValue value) {
            ((IDictionary<MString, TValue>)Value).Add(key, value);
        }

        public void Clear() {
            ((IDictionary<MString, TValue>)Value).Clear();
        }

        public bool Contains(KeyValuePair<MString, TValue> item) {
            return ((IDictionary<MString, TValue>)Value).Contains(item);
        }

        public bool ContainsKey(string key) {
            return ContainsKey(new MString(key));
        }

        public bool ContainsKey(MString key) {
            return ((IDictionary<MString, TValue>)Value).ContainsKey(key);
        }

        public void CopyTo(KeyValuePair<MString, TValue>[] array, int arrayIndex) {
            ((IDictionary<MString, TValue>)Value).CopyTo(array, arrayIndex);
        }

        public IEnumerator<KeyValuePair<MString, TValue>> GetEnumerator() {
            return ((IDictionary<MString, TValue>)Value).GetEnumerator();
        }

        public bool Remove(KeyValuePair<MString, TValue> item) {
            return ((IDictionary<MString, TValue>)Value).Remove(item);
        }

        public bool Remove(string key) {
            return Remove(new MString(key));
        }

        public bool Remove(MString key) {
            return ((IDictionary<MString, TValue>)Value).Remove(key);
        }

        public bool TryGetValue(MString key, out TValue value) {
            return ((IDictionary<MString, TValue>)Value).TryGetValue(key, out value);
        }

        IEnumerator IEnumerable.GetEnumerator() {
            return ((IDictionary<MString, TValue>)Value).GetEnumerator();
        }
    }

    public static Message Convert(object obj) {
        if (obj.GetType() == typeof(byte)) {
            return new MByte((byte)obj);
        } else if (obj.GetType() == typeof(char)) {
            return new MChar((char)obj);
        } else if (obj.GetType() == typeof(short)) {
            return new MShort((short)obj);
        } else if (obj.GetType() == typeof(ushort)) {
            return new MUShort((ushort)obj);
        } else if (obj.GetType() == typeof(int)) {
            return new MInt((int)obj);
        } else if (obj.GetType() == typeof(uint)) {
            return new MUInt((uint)obj);
        } else if (obj.GetType() == typeof(long)) {
            return new MLong((long)obj);
        } else if (obj.GetType() == typeof(ulong)) {
            return new MULong((ulong)obj);
        } else if (obj.GetType() == typeof(float)) {
            return new MFloat((float)obj);
        } else if (obj.GetType() == typeof(double)) {
            return new MDouble((double)obj);
        } else if (obj.GetType() == typeof(string)) {
            return new MString((string)obj);
        } else if (obj.GetType() == typeof(List<Message>)) {
            return new MList<Message>((List<Message>)obj);
        } else if (obj.GetType() == typeof(Dictionary<MString, Message>)) {
            return new MDictionary<MString, Message>((Dictionary<MString, Message>)obj);
        } else if(obj is Message) {
            return (Message)obj;
        }

        throw new NotImplementedException();
    }
}