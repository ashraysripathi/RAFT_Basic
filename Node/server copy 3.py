from concurrent.futures import thread
import socket
import time
import threading
import traceback
import json
import os
import random
import math
from queue import Queue

SERVER_ID = int(os.environ['SERVER_ID'])
NUM_SERVERS = int(os.environ['NUM_SERVERS'])
NODE_NAME = str(os.environ['SERVER_NAME'])
#print(type(NODE_NAME))
###################################### RAFT LEADER ELECTION###############################################
FOLLOWER = 0
CANDIDATE = 1
LEADER = 2
votedFor = None
currentTermVotes = 0
log = []
state = FOLLOWER
lastIndex = 0
term = 0
heartbeat = 0.15
msg_main = {
    "sender_name": NODE_NAME,
    "request": "",
    "term": term,
    "key": "",
    "value": "",
    "votedFor": ""
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


def listener(skt, out_q, msg_out):
    print(f"Starting Listener")
    hbtimeout = True
    while True:
        print("Listener Active")
        st = 0
        et = time.time()
        #msg = {}

        try:
            #time.sleep(5)
            ##print("message not received yet")
            # msg, addr = skt.recvfrom(1024)

            if state == FOLLOWER and hbtimeout:

                skt.settimeout(random.uniform(0.450, 0.500))
            if state == CANDIDATE:
                skt.settimeout(None)
            msg, addr = skt.recvfrom(1024)

            ##print("message recieved")
        except socket.timeout:
            print("Timeout")
            #print("ReqVoteRPC")
            skt.settimeout(None)
            instr = "TIMEOUT"
            out_q.put(instr)
            continue
            #time.sleep(1)
            #decoded_msg = ""
            #break
        except:
            print(
                f"ERROR while fetching from socket : {traceback.print_exc()}")
        #time.sleep(1)
        # Decoding the Message received from Node 1
        decoded_msg = json.loads(msg.decode('utf-8'))
        if decoded_msg['request'] == "AppendEntryRPC":
            hbtimeout = True
        if decoded_msg['request'] == "RequestVoteRPC":
            #print("VOTE_REQ")
            hbtimeout = False
            skt.settimeout(None)
            out_q.put("VOTE_REQ")
            msg_out.put(decoded_msg)
            #break
        if decoded_msg['request'] == "vote":
            out_q.put("VOTE_RESP")
            msg_out.put(decoded_msg)
            #break
        print(f"Message Received : {decoded_msg} From : {addr}")
        st = time.time()

        print("time btwn msgs", st - et)

        st += et
        #if decoded_msg['counter'] >= 99:
        #break

    print("Exiting Listener Function")


def sender(skt, in_q, msg_in):
    print("Starting Sender")
    type = 0
    global state, term, votedFor
    instr = None
    msg = {'request': ''}
    #msg = {'request': ''}

    while True:
        #print("Sender Active")
        #time.sleep(5)
        #print("before reading")
        #print("S???")

        try:
            instr = in_q.get_nowait()
            # print("instr", instr)
            msg = msg_in.get_nowait()
            #print("MESSAGE", msg)

        except:
            pass

        #print("after reading", instr)
        if state == LEADER:
            print("STATE", state)
            generateAndSendAppendRPC()

        if instr == "TIMEOUT":
            print("STATE", state)
            print("sendingVoteRPC")
            sendRequestVoteRPC()
            #instr = None
            #in_q.queue.clear()
        if instr == "VOTE_REQ":
            #print("STATE", state)
            #print("VOTE_REQ")
            #in_q.queue.clear()
            if msg['request'] == 'RequestVoteRPC':
                #print("Received Request")
                # print("term", term, "votedFor", votedFor)
                # print(msg['term'])
                #voteReply(msg)
                if msg['term'] >= term and votedFor == None:

                    print("Valid Request")

                    voteReply(msg)
                    term = msg['term']
                    votedFor = msg['sender_name']
                    #break
        if instr == "VOTE_RESP":
            if msg['request'] == 'vote':
                recvVote()
        #in_q.queue.clear()


def recvVote():
    global state, currentTermVotes
    currentTermVotes += 1
    if currentTermVotes >= math.ceil(NUM_SERVERS / 2):
        state = LEADER


def voteReply(msg):
    target = msg['sender_name']
    #clearMsg(msg)
    msg['request'] = "vote"
    msg['votedFor'] = votedFor
    print("voting for,", target, "msg=", msg)
    reply_rpc_json = json.dumps(msg).encode()
    print("voting for,", target)
    try:
        UDP_Socket.sendto(reply_rpc_json, (target, 5555))
        print("Vote complete")
    except:
        print("Failed to send to ", target)


def create_msg():
    msg = msg = {"msg": f"Hi, I am Node", "counter": "00"}
    msg_bytes = json.dumps(msg).encode()
    return msg_bytes


def function_to_demonstrate_multithreading():
    for i in range(5):
        print(f"Hi Executing Dummy function : {i}")
        time.sleep(2)


def clearMsg(msg):
    msg.fromkeys(msg, None)


def generateAndSendAppendRPC():
    #print("Executing?")
    time.sleep(0.15)  # THIS SEEMS TO CONTROL THE TIMER. WHY.
    msg_main['request'] = "AppendRPC"
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
        print("sending to ", target, "term", term)
        UDP_Socket.sendto(arpc_json, (target, 5555))


    #threading.Timer(0.15, generateAndSendAppendRPC())
def get_sname(server_id):
    sname = "Node"
    sname += str(i)
    return sname


def sendRequestVoteRPC():
    global term, state
    msg_main["leaderID"] = None
    term = term + 1
    state = CANDIDATE
    msg_main['request'] = "RequestVoteRPC"
    msg_main['term'] = term
    msg_main['lastLogIndex'] = 0
    msg_main['lastLogTerm'] = 0
    msg_main['candidateId'] = SERVER_ID
    rrpc_json = json.dumps(msg_main).encode()
    for node in MESSAGE_LIST:
        target = node
        #print("sending to ", target)
        try:
            UDP_Socket.sendto(rrpc_json, (target, 5555))
        except:

            print("Failed to send to ", node)


def print_hello():
    print("hello world")


if __name__ == "__main__":
    #print(os.environ)

    #print("ServerName", NODE_NAME)

    #print("testmessage1")
    #print("Main")

    time.sleep(5)
    print("Starting Node")
    q = Queue()
    msg_q = Queue()
    #USE 2 QUEUES
    threading.Thread(target=listener, args=(UDP_Socket, q, msg_q)).start()
    time.sleep(1)
    threading.Thread(target=sender, args=(UDP_Socket, q, msg_q)).start()
    time.sleep(1)

    q.join()
    msg_q.join()
