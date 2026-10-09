import json
import socket
import sys
import threading
import uuid
from datetime import datetime

UDP_PORT = 54321
BROADCAST_ADDR = "255.255.255.255" # broadcast address for peer discovery
NODE_ID = uuid.uuid4().hex[:8]    # unique per process, used to ignore own broadcasts
TCP_PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 12345 # specific TCP port when testing on the same machine

def log_msg(msg, sent, addr):
    with open("log2.txt", "a") as log:
        if(sent):
            log.write(f"[{datetime.now():%H:%M:%S.%f}] Sent {msg.get("type")} to {addr}: {msg}\n")
        else:
            log.write(f"[{datetime.now():%H:%M:%S.%f}] Receieved {msg.get("type")} from {addr}: {msg}\n")

# broadcast peer_request and collect peer_acks on start
def send_peer_request():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1) # enable broadcasting on this UDP socket

        msg = {"type": "peer_request", "node_id": NODE_ID}# protocol message for peer discovery
        sock.sendto(json.dumps(msg).encode(), (BROADCAST_ADDR, UDP_PORT))
        #log that we sent peer request
        print(f"[discovery] broadcasting peer_request")
        log_msg(msg, True, "BROADCAST")

        #sock.settimeout(3)
        while True:
            try:
                response, addr = sock.recvfrom(4096)
            except socket.timeout:  # nobody answered for 3 sec, so we're done
                print("[discovery] no peer_acks received, done waiting")
                break
            try:
                ack = json.loads(response.decode()) # got something, try to parse it
            except (json.JSONDecodeError, UnicodeDecodeError): # got junk or malformed response, continue with the next response
                print(f"[discovery] junk reply from {addr}, ignoring")
                continue
            if ack.get("type") == "peer_ack" and ack.get("node_id") != NODE_ID: # valid peer_ack from another node
                print(f"[discovery] got peer_ack from {addr[0]}, tcp_port={ack['tcp_port']}, id={ack['node_id']}. Starting TCP connection")
                #log the peer ack receieved
                log_msg(ack, False, addr)
                # later: connect over TCP here for each peer_ack received


def udp_listener():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    if hasattr(socket, "SO_REUSEPORT"):      # not on Windows
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    sock.bind(("", UDP_PORT))
    print(f"[listener] listening on UDP {UDP_PORT}")

    while True:
        data, addr = sock.recvfrom(4096)
        try:
            msg = json.loads(data.decode())
        except (json.JSONDecodeError, UnicodeDecodeError):
            print(f"[listener] junk packet from {addr}, ignoring")
            continue

        if msg.get("type") != "peer_request": #this listener only handles peer_request messages and send acknowledgments
            continue
        if msg.get("node_id") == NODE_ID: # ignore our own broadcast
            print("[listener] ignored my own broadcast")
            continue

        #Log that we recieved peer request
        print(f"[listener] got peer_request from {addr}, id={msg['node_id']}")
        log_msg(msg, False, addr)
        ack = {"type": "peer_ack", "node_id": NODE_ID, "tcp_port": TCP_PORT} # peer ack protocol message
        sock.sendto(json.dumps(ack).encode(), addr)   # reply directly to sender
        #log that we sent the peer ack
        print(f"[listener] sent peer_ack to {addr}, node_id={ack['node_id']}")
        log_msg(ack, True, addr)


print(f"My id={NODE_ID}, tcp_port={TCP_PORT}")
# listener first, so we're ready before we announce ourselves
threading.Thread(target=udp_listener, daemon=True).start()
send_peer_request()