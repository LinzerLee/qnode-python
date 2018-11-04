using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class MRegister : Message {
    public string User;
    public string Password;
}

public class MRegisterRep : Message {
    //  ErrorCode : 业务处理结果代码
    //  0 : 注册成功
    //  1 : 用户已存在
    //  2 : 用户名不合法
    //  3 : 密码输入不合法
    public int ErrorCode;
    // 用户登录码
    public Guid LoginCode;
}

public class MLogin : Message {
    public string User;
    public string Password;
}

public class MLoginrRep : Message {
    //  ErrorCode : 业务处理结果代码
    //  0 : 登录成功
    //  1 : 用户不存在
    //  2 : 密码错误
    //  3 : 账号冻结
    public int ErrorCode;
    // 用户登录码
    public Guid LoginCode;
}

public class MLogout : Message {
    // 用户登录码
    public Guid LoginCode;
}

public class MLogoutRep : Message {
    //  ErrorCode : 业务处理结果代码
    //  0 : 登出成功
    //  1 : 登出失败
    public int ErrorCode;
}