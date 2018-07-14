#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import socket
import queue
import threading as th
import copy
import random
import time

# server监听地址
server_addr = '127.0.0.1'
# server监听端口
server_port = 8999
# 通信线程tcp每次接受的字节数
tcp_bit = 1024
# 通信编码
tcp_coding = 'utf-8'


def client_main():
    # 初始化state
    state = {'turn': 0, 'flag': 0, 'player_0': {'used': 0, 'remain': 0, 'score': 0}, 'player_1': {
        'used': 0, 'remain': 0, 'score': 0}}
    # 多线程控制
    control_dct = {'state': th.Lock(), 'next': th.Event(),
                   'stop': th.Event()}
    '''
    state - state的读写权限
    next - tcp通知game进入下回合
    stop - 通知各线程游戏结束
    '''
    msg_queue = queue.Queue()
    # 游戏逻辑线程
    thread_game = th.Thread(target=game, args=(state, control_dct, msg_queue))
    thread_game.start()
    # 连接服务器
    client = socket.socket()
    try:
        client.connect((server_addr, server_port))
    except:
        print('Error: cannot connect with server')
        return
    # 发送线程
    thread_recv = th.Thread(
        target=client_recv, args=(client, state, control_dct))
    # 接收线程
    thread_send = th.Thread(target=client_send, args=(
        client, control_dct, msg_queue))
    thread_recv.start()
    thread_send.start()
    thread_recv.join()
    thread_game.join()
    thread_send.join()


def client_recv(sock, state, control_dct):
    '''
    接收server的回合信息并写入state
    同时控制程序的结束
    '''
    while True:
        data = b''
        while True:
            buffer = sock.recv(tcp_bit)
            # server 断开连接
            if buffer == b'':
                print('Error: cannot connect with server')
                control_dct['stop'].set()
                control_dct['next'].set()
                return
            elif len(buffer) < tcp_bit:
                data += buffer
                break
            else:
                data += buffer
        # 数据解析
        if data != b'':
            try:
                msg_recv = json.loads(data.decode(tcp_coding))
            except:
                print('Error: cannot load message from server')
            control_dct['state'].acquire()
            # 游戏已经结束
            if 'winner' in msg_recv:
                if msg_recv['winner'] == state['flag']:
                    print('WON')
                elif msg_recv['winner'] == 1-state['flag']:
                    print('LOST')
                elif msg_recv['winner']==-1:
                    print('DRAW')
                else:
                    print('Error: incomplete/improper message')
                control_dct['state'].release()
                control_dct['stop'].set()
                control_dct['next'].set()
                return
            # 写入state
            try:
                state['turn'] = msg_recv['turn']
                state['flag'] = msg_recv['flag']
                state['player_0'] = msg_recv['player_0']
                state['player_1'] = msg_recv['player_1']
            except:
                print('Error: incomplete/improper message')
            control_dct['state'].release()
            # 通知game进入下一回合
            control_dct['next'].set()


def client_send(sock, control_dct, msg_queue):
    '''
    发送所有来自game的消息
    '''
    while True:
        msg = msg_queue.get()
        # 检查程序是否结束
        if control_dct['stop'].isSet():
            sock.close()
            return
        try:
            sock.sendall(bytes(json.dumps(msg), encoding=tcp_coding))
        except:
            print('Error: cannot send message to server')


def game(__state, control_dct, msg_queue):
    '''
    游戏逻辑处理
    '''
    while True:
        # 进入下回合
        control_dct['next'].wait()
        control_dct['next'].clear()
        # 检查程序是否结束
        if control_dct['stop'].isSet():
            msg_queue.put({})
            return
        # 复制state的副本
        control_dct['state'].acquire()
        state = copy.deepcopy(__state)
        control_dct['state'].release()
        # 游戏逻辑部分
        p = random.random()
        used = 0
        if p < 0.5:
            used = random.randint(0, 1000)
        elif p < 1:
            sleep_time = random.uniform(0.5, 10)
            time.sleep(sleep_time)
            used = random.randint(0, 1000)
        else:
            print("enter endless loop")
            while True:
                pass
        # 发送消息
        msg = {'turn': state['turn']+1, 'used': used}
        msg_queue.put(msg)


def main():
    client_main()


if __name__ == '__main__':
    main()
