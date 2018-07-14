#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import socket
import queue
import threading as th
import copy
import random
import time

# 通信线程tcp每次接受的字节数
tcp_bit = 1024
# 通信编码
tcp_coding = 'utf-8'


def client_main(server_addr='127.0.0.1', server_port=8999):
    state = {'turn': 0, 'flag': 0, 'player_0': {'used': 0, 'remain': 0, 'score': 0}, 'player_1': {
        'used': 0, 'remain': 0, 'score': 0}}
    control_dct = {'state': th.Lock(), 'next_turn': th.Event(),
                   'stop': th.Event()}
    msg_queue = queue.Queue(1)
    thread_game = th.Thread(target=game, args=(state, control_dct, msg_queue))
    thread_game.start()
    client = socket.socket()
    try:
        client.connect((server_addr, server_port))
    except:
        print('Error: cannot connect with server')
        # 处理结束
        return
    thread_recv = th.Thread(
        target=client_recv, args=(client, state, control_dct))
    thread_send = th.Thread(target=client_send, args=(
        client, control_dct, msg_queue))
    thread_recv.start()
    thread_send.start()
    thread_recv.join()
    thread_game.join()
    thread_send.join()


def client_recv(sock, state, control_dct):
    while True:
        data = b''
        while True:
            buffer = sock.recv(tcp_bit)
            if buffer == b'' or buffer == b'{}':  # server 断开连接或退出
                control_dct['stop'].set()
                control_dct['next_turn'].set()
                return
            elif len(buffer) < tcp_bit:
                data += buffer
                break
            else:
                data += buffer
        if data == b'':
            pass  # server 断开连接
        else:
            # 数据解析
            try:
                msg_recv = json.loads(data.decode(tcp_coding))
            except:
                print('Error: cannot load message from server')
            # 数据解析
            control_dct['state'].acquire()
            try:
                state['turn'] = msg_recv['turn']
                state['flag'] = msg_recv['flag']
                state['player_0'] = msg_recv['player_0']
                state['player_1'] = msg_recv['player_1']
            except:
                print('Error: incomplete message')
            control_dct['state'].release()
            control_dct['next_turn'].set()


def client_send(sock, control_dct, msg_queue):
    while True:
        msg = msg_queue.get()
        if control_dct['stop'].isSet():
            sock.close()
            return
        try:
            sock.sendall(bytes(json.dumps(msg), encoding=tcp_coding))
        except:
            print('Error: cannot send message to server')


def game(__state, control_dct, msg_queue):
    while True:
        control_dct['next_turn'].wait()
        control_dct['next_turn'].clear()
        if control_dct['stop'].isSet():
            msg_queue.put({})
            return
        control_dct['state'].acquire()
        state = copy.deepcopy(__state)
        control_dct['state'].release()

        p = random.random()
        used = 0
        if p < 0.5:
            used = random.randint(0, 1000)
        elif p < 0.9:
            sleep_time = random.uniform(0.5, 10)
            time.sleep(sleep_time)
            used = random.randint(0, 1000)
        else:
            print("enter endless loop")
            while True:
                pass
        msg = {'turn': state['turn']+1, 'used': used}
        msg_queue.put(msg)


def main():
    client_main()


if __name__ == '__main__':
    main()
