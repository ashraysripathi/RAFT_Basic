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
# print(type(NODE_NAME))
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
timeout = random.uniform(0.450, 0.500) * 1000
leaderID = None
commitIndex = 0
lastApplied = 0
prevLogIndex = 0
prevLogIndex = 0
prevLogTerm = 0
matchMajority = 0

nextIndex = lastIndex+1
matchIndex = 0

entry = {}

msg_main = {
    "sender_name": NODE_NAME,
    "request": "",
    "term": term,
    "key": "",
    "value": "",
    "votedFor": None,
    "commitIndex": commitIndex,
    "success": None,
    "entry": entry,
    "matchIndex": matchIndex

}
msg_store = {}


MESSAGE_LIST = []
for i in range(1, int(NUM_SERVERS) + 1):
    if (i != SERVER_ID):
        send = "Node"
        send += str(i)
        MESSAGE_LIST.append(send)
# print(MESSAGE_LIST)
sender = ""
if SERVER_ID == 1:
    sender = "Node1"
elif SERVER_ID == 2:
    sender = "Node2"
elif SERVER_ID == 3:
    sender = "Node3"
elif SERVER_ID == 4:
    sender = "Node4"
elif SERVER_ID == 5:
    sender = "Node5"
UDP_Socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
#UDP_Socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
UDP_Socket.bind((sender, 5555))


def listener(skt, out_q, msg_out):
    global state, msg_store, timeout, term, votedFor, log, entry, leaderID, matchIndex, prevLogIndex, commitIndex, prevLogTerm
    print(f"Starting Listener")
    hbtimeout = True
    while True:
        timeout = random.uniform(0.450, 0.500)
        print("Listener Active")
        st = 0
        et = time.time()
        #msg = {}
        print("Votes:", currentTermVotes)

        try:
            # time.sleep(5)
            ##print("message not received yet")
            # msg, addr = skt.recvfrom(1024)

            if state == FOLLOWER and hbtimeout:

                skt.settimeout(timeout)
            if state == CANDIDATE:
                print("Socket_Timeout Candidate")
                skt.settimeout(None)
            msg, addr = skt.recvfrom(1024)

            ##print("message recieved")
        except socket.timeout:
            print("Timeout")
            # print("ReqVoteRPC")
            print("Socket_Timeout Timeout")
            skt.settimeout(None)
            instr = "TIMEOUT"
            out_q.put(instr)
            msg_q.put(msg_store)
            continue
            # time.sleep(1)
            #decoded_msg = ""
            # break
        except:
            print(
                f"ERROR while fetching from socket : {traceback.print_exc()}")
        # time.sleep(1)
        # Decoding the Message received from Node 1
        decoded_msg = json.loads(msg.decode('utf-8'))

        if decoded_msg['request'] == "AppendRPC":
            if term < decoded_msg['term']:
                term = decoded_msg['term']
                writeToStorage()
            if decoded_msg['term'] < term:
                out_q.put("REPLYFALSE")
                msg_out.put(decoded_msg)
            else:
                out_q.put("REPLYTRUE")
                msg_out.put(decoded_msg)
            print("ENTRY", decoded_msg['entry'])
            if decoded_msg['entry'] != {}:
                if prevLogIndex == 0:
                    log.append(decoded_msg['entry'])
                    matchIndex += 1

                else:
                    try:
                        check = log[decoded_msg['prevLogIndex']]
                        if(check['term'] != prevLogTerm):
                            out_q.put("REPLYFALSE")
                            msg_out.put(decoded_msg)
                        elif(log[-1] != decoded_msg['entry']):
                            log.append(decoded_msg['entry'])
                        matchIndex += 1

                    except IndexError:
                        out_q.put("REPLYFALSE")
                        msg_out.put(decoded_msg)

            if decoded_msg["commitIndex"] > commitIndex:
                commitIndex = decoded_msg["commitIndex"]
                writeToLog()
                #print("Follower Log", log)

            skt.settimeout(timeout)
            state = FOLLOWER
            hbtimeout = True
            leaderID = decoded_msg['leaderID']
            # update term

            out_q.queue.clear()
            # continue

        if decoded_msg['request'] == "RequestVoteRPC":
            # print("VOTE_REQ")
            hbtimeout = False
            print("Socket_Timeout ReqVoteRPC")
            skt.settimeout(None)
            out_q.put("VOTE_REQ")
            msg_out.put(decoded_msg)
            # break
        if decoded_msg['request'] == "vote":
            out_q.put("VOTE_RESP")
            msg_out.put(decoded_msg)
            # break
        if decoded_msg['request'] == 'CONVERT_FOLLOWER':
            state = FOLLOWER
            hbtimeout = True
        if decoded_msg['request'] == 'LEADER_INFO':
            if state == LEADER:
                decoded_msg['key'] = "LEADER"
                decoded_msg['value'] = NODE_NAME
            else:
                decoded_msg['key'] = "LEADER"
                decoded_msg['value'] = get_sname(msg_store['leaderID'])
            ctrl_json = json.dumps(decoded_msg).encode()
            UDP_Socket.sendto(ctrl_json, ('Controller', 5555))
        if decoded_msg['request'] == 'SHUTDOWN':
            # print("hmm")
            break
        if decoded_msg['request'] == 'STORE':
            if state == LEADER:
                print("Handle Store Request")

                entry['term'] = term
                entry['key'] = decoded_msg['key']
                entry['value'] = decoded_msg['value']
                log.append(entry)
                print(log)
                out_q.put("STORE")
                decoded_msg['request'] = ""

            else:
                op_msg = {}
                op_msg['sender_name'] = sender
                op_msg['term'] = None
                op_msg['request'] = "LEADER_INFO"
                op_msg['key'] = "LEADER"
                op_msg['value'] = get_sname(leaderID)
            ctrl_json = json.dumps(decoded_msg).encode()
            UDP_Socket.sendto(ctrl_json, ('Controller', 5555))

        if decoded_msg['request'] == 'RETRIEVE':
            if state == LEADER:
                print("Handle Retrieve Request")
            else:
                decoded_msg['key'] = "LEADER"
                decoded_msg['value'] = get_sname(leaderID)
                ctrl_json = json.dumps(decoded_msg).encode()
            UDP_Socket.sendto(ctrl_json, ('Controller', 5555))

        if decoded_msg['request'] == 'AppendReply':
            if decoded_msg['success'] == False:
                instr = "TIMEOUT"
                out_q.put(instr)
            if decoded_msg['matchIndex'] > matchIndex:
                majority = recvMatch()
                if(majority):
                    matchIndex = decoded_msg['matchIndex']
                    prevLogTerm = log[prevLogIndex]['term']
                    commitIndex += 1
                    prevLogIndex += 1

                    writeToLog()

        #msg_store['leaderID'] = decoded_msg['leaderID']
        if decoded_msg['request'] == 'TIMEOUT':
            instr = "TIMEOUT"
            out_q.put(instr)

        print(f"Message Received : {decoded_msg} From : {addr}")
        #print("Msg_main=", msg_main)
        st = time.time()
        #msg_store['leaderID'] = decoded_msg['leaderID']
        print("time btwn msgs", st - et)
        print("Current Term :", term)
        print("Log", log)

        st += et
        # if decoded_msg['counter'] >= 99:
        # break

    print("Exiting Listener Function")


def sender(skt, in_q, msg_in):
    print("Starting Sender")
    #type = 0
    global state, term, votedFor, log, entry
    instr = None
    msg = {'request': ''}
    ackflag = False
    #msg = {'request': ''}
    print("ack", ackflag)
    while True:
        #print("Sender Active")
        # time.sleep(5)
        #print("before reading")
        # print(instr)

        try:
            instr = in_q.get_nowait()
            # print("instr", instr)
            msg = msg_in.get_nowait()
            #print("MESSAGE", msg)

        except:
            pass

        #print("after reading", instr)

        if instr == "TIMEOUT" and ackflag == False:

            #print("STATE", state)
            # print("sendingVoteRPC")
            sendRequestVoteRPC()
            ackflag = True
            continue
            #instr = None
            # in_q.queue.clear()

            #ackflag = False
        if instr == "VOTE_REQ":
            #print("STATE", state)
            # print("VOTE_REQ")
            # in_q.queue.clear()
            # print(msg)
            if msg['request'] == 'RequestVoteRPC':
                #print("Received Request")
                #print("term", term, "votedFor", votedFor)
                #print("Msg-term", msg['term'])
                # voteReply(msg)
                if msg['term'] >= term and votedFor == None:

                    print(" SENDER Valid Request")

                    voteReply(msg)
                    term = msg['term']
                    votedFor = msg['sender_name']
                    state = FOLLOWER
                    # break

        if instr == "VOTE_RESP":
            if msg['request'] == 'vote':
                recvVote()
                ackflag = False
            msg_in.queue.clear()

        if instr == "STORE":
            print("Send to Other nodes")
            if entry != {}:
                sendEntryStore()
            instr = ""

        if instr == "REPLYFALSE":
            #print("Send to Other nodes")
            success = False
            AppendReply(success, msg)
            entry = {}

        if instr == "REPLYTRUE":
            #print("Send to Other nodes")
            success = True
            AppendReply(success, msg)
            entry = {}

        if state == LEADER:
            #print("STATE", state)
            generateAndSendAppendRPC()
            instr = ""
        # in_q.queue.clear()


def recvMatch():
    global matchMajority
    matchMajority += 1
    if matchMajority >= math.ceil(NUM_SERVERS / 2):
        matchMajority = 0
        return True

    return False


def AppendReply(success, msg):
    if success == True:
        #print("Reply True")
        target = msg['sender_name']
        msg_main['request'] = "AppendReply"
        msg_main['success'] = True
        msg_main['matchIndex'] = matchIndex
        reply_rpc_json = json.dumps(msg_main).encode()
        try:
            UDP_Socket.sendto(reply_rpc_json, (target, 5555))
            #print("Vote complete")

        except:
            print("ReplyACK Failed to send to ", target)

    elif success == False:
        target = msg['sender_name']
        msg_main['request'] = "AppendReply"
        msg_main['success'] = False
        reply_rpc_json = json.dumps(msg_main).encode()
        try:
            UDP_Socket.sendto(reply_rpc_json, (target, 5555))
            print("Vote complete")

        except:
            print("ReplyACK Failed to send to ", target)

        #print("Reply False")


def sendEntryStore():
    global entry
    msg_main['request'] = "AppendRPC"
    msg_main['term'] = term
    msg_main['leaderID'] = SERVER_ID
    msg_main['prevLogIndex'] = prevLogIndex
    if msg_main['prevLogIndex'] == prevLogIndex:
        msg_main['prevLogTerm'] = prevLogTerm
    else:
        msg_main['prevLogTerm'] = prevLogTerm
    msg_main['entry'] = entry

    arpc_json = json.dumps(msg_main).encode()
    for node in MESSAGE_LIST:

        target = node
        #UDP_Socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        #print("sending to ", target, "term", term)
        try:
            UDP_Socket.sendto(arpc_json, (target, 5555))
        except:
            print("AppendRPC Failed to send to ", node)
    msg_main['entry'] = {}


def recvVote():
    global state, currentTermVotes
    currentTermVotes += 1
    if currentTermVotes >= math.ceil(NUM_SERVERS / 2):
        state = LEADER
        writeToStorage()


def voteReply(msg):
    target = msg['sender_name']
    # clearMsg(msg)
    msg['request'] = "vote"
    msg['votedFor'] = votedFor
    print("voting for,", target, "msg=", msg)
    reply_rpc_json = json.dumps(msg).encode()
    print("voting for,", target)

    try:
        UDP_Socket.sendto(reply_rpc_json, (target, 5555))
        print("Vote complete")

    except:
        print("ReplyACK Failed to send to ", target)


def writeToStorage():
    fstore = {
        "currentTerm": term,
        "votedFor": votedFor,
        "log": log,
        "timeout": timeout,
        "heartbeat": 150
    }
    jstring = json.dumps(fstore)
    jsonFile = open("data.json", "a")
    jsonFile.write(jstring)
    jsonFile.close()


def writeToLog():
    logfile = open("log.json", "a")
    for element in log:
        jstring = json.dumps(element)
        logfile.write(jstring)
    logfile.close()


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
    # print("Executing?")
    time.sleep(0.15)  # THIS SEEMS TO CONTROL THE TIMER. WHY.
    msg_main['request'] = "AppendRPC"
    msg_main['term'] = term
    msg_main['leaderID'] = SERVER_ID
    msg_main['prevLogIndex'] = prevLogIndex
    if msg_main['prevLogIndex'] == prevLogIndex:
        msg_main['prevLogTerm'] = prevLogTerm
    else:
        msg_main['prevLogTerm'] = prevLogTerm
        # handle prevLogTerm somehow
    msg_main["commitIndex"] = commitIndex
    arpc_json = json.dumps(msg_main).encode()
    msg_main['entry'] = {}
    # print(MESSAGE_LIST)
    #print("CVT:", currentTermVotes)
    for node in MESSAGE_LIST:

        target = node
        #UDP_Socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        #print("sending to ", target, "term", term)
        try:
            UDP_Socket.sendto(arpc_json, (target, 5555))
        except:
            print("AppendRPC Failed to send to ", node)

    #threading.Timer(0.15, generateAndSendAppendRPC())


def get_sname(server_id):
    sname = "Node"
    sname += str(server_id)
    return sname


def sendRequestVoteRPC():
    global term, state, currentTermVotes
    msg_main["leaderID"] = None
    term = term + 1
    state = CANDIDATE
    msg_main['request'] = "RequestVoteRPC"
    msg_main['term'] = term
    msg_main['lastLogIndex'] = 0
    msg_main['lastLogTerm'] = 0
    msg_main['candidateId'] = SERVER_ID
    currentTermVotes = 1
    rrpc_json = json.dumps(msg_main).encode()
    for node in MESSAGE_LIST:
        target = node
        print("SRPC sending to ", target)
        try:
            UDP_Socket.sendto(rrpc_json, (target, 5555))
        except:
            print("SRPC Failed to send to ", node)


def print_hello():
    print("hello world")


if __name__ == "__main__":
    # print(os.environ)

    #print("ServerName", NODE_NAME)

    # print("testmessage1")
    # print("Main")

    time.sleep(5)
    print("Starting Node")
    q = Queue()
    msg_q = Queue()
    # USE 2 QUEUES
    threading.Thread(target=listener, args=(UDP_Socket, q, msg_q)).start()
    time.sleep(1)
    threading.Thread(target=sender, args=(UDP_Socket, q, msg_q)).start()
    time.sleep(1)

    q.join()
    msg_q.join()
    # time.sleep(10)
