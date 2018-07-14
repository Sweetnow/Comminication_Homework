# 网络通信开发 小游戏

    作者：张钧
------

## server.py

### 主要逻辑

    设置计时器线程timer处理整体时序与进程结束，逻辑处理线程game处理每回合结算，通信线程tcp处理与client的通信

### 可修改参数

    (见server.py头部)

1. server监听地址

2. server监听端口

3. 一回合最长时间(s)

4. 计时线程timer每次睡眠时长(s)

5. 通信线程tcp每次睡眠时长(s)

6. 通信线程tcp每次接受的字节数

7. 通信编码

8. 起始筹码数

9. 最大回合数

------

## client.py

### 主要逻辑

    设置client_recv处理信息接收与进程结束，client_send处理信息发送，game处理游戏逻辑

### 可修改参数

    (见client.py头部)

1. server监听地址

2. server监听端口

3. 通信线程tcp每次接受的字节数

4. 通信编码

------

