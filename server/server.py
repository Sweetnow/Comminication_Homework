#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import threading as th
import socket
import json
import time
import queue

# 一回合最长时间(s)
turn_time = 1
# 计时线程timer每次睡眠时长(s)
timer_sleep = 0.05
# 通信线程tcp每次睡眠时长(s)
tcp_sleep = 0.005
# 通信线程tcp每次接受的字节数
tcp_bit = 1024
# 通信编码
tcp_coding = 'utf-8'
# 起始筹码数
game_coin = 1000
# 最大回合数
max_turn = 50
turn = 0


def server_main(server_addr='127.0.0.1', server_port=8999):
    server = socket.socket()
    server.bind((server_addr, server_port))
    server.listen(2)
    count = 0
    control_dct = {'start': th.Event(), 'send': th.Event(), 'stop': th.Event(),
                   0: {'next': th.Lock(), 'recv': th.Event(), 'send': th.Event()},
                   1: {'next': th.Lock(), 'recv': th.Event(), 'send': th.Event()}}
    game_queue = {0: {'recv': queue.Queue(1), 'send': queue.Queue(1)},
                  1: {'recv': queue.Queue(1), 'send': queue.Queue(1)}}

    # 计时器线程
    thread_timer = th.Thread(target=timer, args=(control_dct,))
    thread_timer.start()
    # 游戏处理进程
    thread_game = th.Thread(target=game, args=(game_queue, control_dct))
    thread_game.start()
    thread_tcp = []
    print('Waiting for connection ......')
    while count < 2:
        sock, addr = server.accept()
        thread = th.Thread(target=tcp, args=(
            sock, control_dct, count, game_queue[count]))
        thread.start()
        thread_tcp.append(thread)
        count += 1
        print('player_%d is ready. Address: %s' % (count-1, addr))
    print('Game starts')
    control_dct[0]['send'].wait()
    control_dct[1]['send'].wait()
    control_dct[0]['send'].clear()
    control_dct[1]['send'].clear()
    control_dct['start'].set()
    thread_game.join()
    thread_timer.join()
    for i in thread_tcp:
        i.join()


def tcp(sock, control_dct, number, this_queue):
    ''' 
    sock - 与client的套接字
    control_dct - 存储多线程控制Event, Lock的字典
    number - client标号
    this_queue - 与game线程信息交换

    初始化客户端
    发送数据
    '''
    msg_send = this_queue['send'].get()
    try:
        sock.sendall(bytes(json.dumps(msg_send), encoding=tcp_coding))
    except:
        print('Error: cannot send message to player_%d' % (number,))
    # 发送数据
    control_dct[number]['send'].set()

    control_dct['start'].wait()
    sock.setblocking(False)

    while True:
        data = b''
        msg_recv = {}
        # 等待timer初始化结束
        control_dct[number]['next'].acquire()
        control_dct[number]['next'].release()

        if control_dct['stop'].isSet():
            this_queue['recv'].put(msg_recv)
            try:
                sock.sendall(b'{}')
            finally:
                sock.close()
                print('tcp %d closes' % (number,))
                return
        while not control_dct['send'].isSet():
            while True:
                try:
                    buffer = sock.recv(tcp_bit)
                except:
                    buffer = b''
                if buffer == b'':
                    break
                elif len(buffer) < tcp_bit:
                    data += buffer
                    break
                else:
                    data += buffer
            if data == b'':
                time.sleep(tcp_sleep)
            else:
                # 数据解析
                try:
                    sdata = data.decode(tcp_coding)
                    last = sdata[sdata.rfind('}{')+1:]
                    msg_recv = json.loads(last)
                except:
                    print('******Error: cannot load message from player_%d****** %s' %
                          (number, data))
                # 数据解析
                control_dct[number]['recv'].set()
                break
        this_queue['recv'].put(msg_recv)
        control_dct['send'].wait()
        # 发送数据
        msg_send = this_queue['send'].get()
        try:
            sock.sendall(bytes(json.dumps(msg_send), encoding=tcp_coding))
        except:
            print('Error: cannot send message to player_%d' % (number,))
        # 发送数据
        control_dct[number]['send'].set()


def timer(control_dct):
    global turn
    control_dct['start'].wait()
    control_dct[0]['next'].acquire()
    control_dct[1]['next'].acquire()
    while True:
        turn += 1
        if turn > max_turn:
            control_dct['stop'].set()
        for number in range(2):
            control_dct[number]['recv'].clear()
            control_dct[number]['send'].clear()
        control_dct['send'].clear()
        start_time = time.time()
        control_dct[0]['next'].release()
        control_dct[1]['next'].release()
        if control_dct['stop'].isSet():
            return
        while time.time()-start_time < turn_time:
            time.sleep(timer_sleep)
            if control_dct[0]['recv'].isSet() and control_dct[1]['recv'].isSet():
                break

        # 要求通信线程发送信息并进入下一回合（等待信息发送完成）
        control_dct[0]['next'].acquire()
        control_dct[1]['next'].acquire()
        control_dct['send'].set()
        control_dct[0]['send'].wait()
        control_dct[1]['send'].wait()


def game(all_queue, control_dct):
    '''
    游戏逻辑：新回合->下注->计分->返回结果->下一回合
    recv格式：
    {'turn': 15, 'used': 5}

    send格式:
    {'turn': 15, 'flag': 0/1, 'player_0': {'used': 5,
        'remain': 89, 'score': 45}, 'player_1':{...}}
    turn 回合数
    flag 玩家标号
    player_? 玩家信息
        used 本回合下注
        remain 剩余筹码，如出现错误以此校准
        score 得分
    '''
    state = {0: {'remain': game_coin, 'score': 0},
             1: {'remain': game_coin, 'score': 0}}
    # 初始化客户端
    send_0 = {'turn': turn, 'flag': 0, 'player_0': {'used': 0, 'remain': state[0]['remain'], 'score': state[0]['score']}, 'player_1': {
        'used': 0, 'remain': state[1]['remain'], 'score': state[1]['score']}}
    all_queue[0]['send'].put(send_0)
    send_1 = {'turn': turn, 'flag': 1, 'player_0': {'used': 0, 'remain': state[0]['remain'], 'score': state[0]['score']}, 'player_1': {
        'used': 0, 'remain': state[1]['remain'], 'score': state[1]['score']}}
    all_queue[1]['send'].put(send_1)
    while True:
        recv = {0: {}, 1: {}}
        recv[0] = all_queue[0]['recv'].get()
        recv[1] = all_queue[1]['recv'].get()
        print('player',0,recv[0])
        print('player',1,recv[1])
        if control_dct['stop'].isSet():
            for i in range(2):
                print('player_%d remains %d coins, Score: %d' %
                      (i, state[i]['remain'], state[i]['score']))
            if state[0]['score'] != state[1]['score']:
                print('Winner is player_%d' %
                      (0 if state[0]['score'] > state[1]['score'] else 1,))
            else:
                print('No Winner')
            return
        used = {0: 0, 1: 0}
        # 合法性检测
        for i in range(2):
            if len(recv[i]) > 0 and recv[i]['turn'] == turn and recv[i]['used'] <= state[i]['remain'] and recv[i]['used'] >= 0:
                used[i] = recv[i]['used']
                state[i]['remain'] -= used[i]
            else:
                # debug
                if len(recv[i]) == 0:
                    pass
                elif recv[i]['turn'] != turn:
                    print("Error: player_%d's turn is % d, server's turn is %d" % (
                        i, recv[i]['turn'], turn))
                elif recv[i]['used'] > state[i]['remain']:
                    print('player_%d used too many coins' % (i,))
                elif recv[i]['used'] < 0:
                    print('stupid player_%d used %d coin' %
                          (i, recv[i]['used']))

        if used[0] > used[1]:
            state[0]['score'] += 2
        elif used[0] == used[1]:
            state[0]['score'] += 1
            state[1]['score'] += 1
        else:
            state[1]['score'] += 2
        print('turn: '+str(turn))
        for i in range(2):
            print('player_%d remains %d coins, Score: %d' %
                  (i, state[i]['remain'], state[i]['score']))
        print('')
        send_0 = {'turn': turn, 'flag': 0, 'player_0': {'used': used[0], 'remain': state[0]['remain'], 'score': state[0]['score']}, 'player_1': {
            'used': used[1], 'remain': state[1]['remain'], 'score': state[1]['score']}}
        all_queue[0]['send'].put(send_0)
        send_1 = {'turn': turn, 'flag': 1, 'player_0': {'used': used[0], 'remain': state[0]['remain'], 'score': state[0]['score']}, 'player_1': {
            'used': used[1], 'remain': state[1]['remain'], 'score': state[1]['score']}}
        all_queue[1]['send'].put(send_1)


def main():
    server_main()


if __name__ == '__main__':
    main()
