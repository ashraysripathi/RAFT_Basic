from concurrent.futures import thread
import socket
import time
import threading
import traceback
import json
import os
import random

SERVER_ID = int(os.environ['SERVER_ID'])
NUM_SERVERS = os.environ['NUM_SERVERS']
NODE_NAME = str(os.environ['SERVER_NAME'])
print(type(NODE_NAME))
###################################### RAFT LEADER ELECTION###############################################

FOLLOWER = 0
CANDIDATE = 1
LEADER = 2
log = []
state = FOLLOWER
global term
term = 0
heartbeat = 0.15
msg_main = {
    "sender_name": NODE_NAME,
    "request": "",
    "term": term,
    "key": "",
    "value": ""
}

MESSAGE_LIST = []
for i in range(1, int(NUM_SERVERS) + 1):
    if (i != SERVER_ID):
        send = "Node"
        send += str(i)
        MESSAGE_LIST.append(send)
#print(MESSAGE_LIST)
sender = ""
if SERVER_ID == 1:
    sender = "Node1"
elif SERVER_ID == 2:
    sender = "Node2"
elif SERVER_ID == 3:
    sender = "Node3"
UDP_Socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
#UDP_Socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
UDP_Socket.bind((sender, 5555))


def listener(skt):
    #print(f"Starting Listener")

    while True:

        st = 0
        et = time.time()
        msg = {}
        try:
            ##print("message not received yet")
            if SERVER_ID == 2 or SERVER_ID == 3:
                skt.settimeout(random.uniform(0.350, 0.400))
            msg, addr = skt.recvfrom(1024)

            ##print("message recieved")
        except socket.timeout:
            print("Timeout")
            print("ReqVoteRPC")
            sendRequestVoteRPC()
            #decoded_msg = ""
            #break
        except:
            print(
                f"ERROR while fetching from socket : {traceback.print_exc()}")

        # Decoding the Message received from Node 1
        decoded_msg = json.loads(msg.decode('utf-8'))
        st = time.time()
        print(f"Message Received : {decoded_msg} From : {addr}")

        print("time btwn msgs", st - et)

        st += et
        #if decoded_msg['counter'] >= 99:
        #break

    print("Exiting Listener Function")


def create_msg():
    msg = msg = {"msg": f"Hi, I am Node", "counter": "00"}
    msg_bytes = json.dumps(msg).encode()
    return msg_bytes


def function_to_demonstrate_multithreading():
    for i in range(5):
        print(f"Hi Executing Dummy function : {i}")
        time.sleep(2)


def generateAndSendAppendRPC():
    #print("Executing?")
    time.sleep(0.15)  # THIS SEEMS TO CONTROL THE TIMER. WHY.

    msg_main['term'] = term
    msg_main['leaderID'] = SERVER_ID
    msg_main['prevLogIndex'] = 0
    if msg_main['prevLogIndex'] == 0:
        msg_main['prevLogTerm'] = 0
    else:
        msg_main['prevLogTerm'] = 0
        #handle prevLogTerm somehow
    arpc_json = json.dumps(msg_main).encode()
    #print(MESSAGE_LIST)
    for node in MESSAGE_LIST:

        target = node
        #UDP_Socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        print("sending to ", target)
        UDP_Socket.sendto(arpc_json, (target, 5555))
    threading.Timer(0.15, generateAndSendAppendRPC())


def sendRequestVoteRPC():

    state = CANDIDATE


def print_hello():
    print("hello world")


if __name__ == "__main__":
    #print(os.environ)

    #print("ServerName", NODE_NAME)

    #print("testmessage1")
    #print("Main")
    time.sleep(10)

    threading.Thread(target=listener, args=[UDP_Socket]).start()
    if SERVER_ID == 1:
        print("Executing?")
        generateAndSendAppendRPC()
