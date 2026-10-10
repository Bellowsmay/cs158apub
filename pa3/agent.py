import json
import socket
import sys
import threading
import uuid
import time
import os 
from datetime import datetime

UDP_PORT = 54321
BROADCAST_ADDR = "255.255.255.255" # broadcast address for peer discovery
NODE_ID = uuid.uuid4().hex[:8]    # unique per process, used to ignore own broadcasts
TCP_PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 12345 # specific TCP port when testing on the same machine
SHARED_DIR = "shared"
peers = {}        # node_id: socket
peer_files = {}   # node_id: list of files that node should have
peers_lock = threading.Lock() # prevent threads from reading/updating peer list at same time 
send_lock = threading.Lock()  # prevent from sending at the same time so that bytes arent mixed together
log_lock = threading.Lock()   # many threads write to the log, keep lines from interleaving


def log_msg(msg, sent, addr):
    with log_lock, open("log.txt", "a") as log:
        if(sent):
            log.write(f"[{datetime.now():%H:%M:%S.%f}] Sent {msg.get("type")} to {addr}: {msg}\n")
        else:
            log.write(f"[{datetime.now():%H:%M:%S.%f}] Receieved {msg.get("type")} from {addr}: {msg}\n")

# log peer table changes (added / removed)
def log_peer_change(action, peer_id, addr):
    with log_lock, open("log.txt", "a") as log:
        log.write(f"[{datetime.now():%H:%M:%S.%f}] Peer {action}: {peer_id} at {addr}\n")

# address of the other end of a TCP socket, for logging
def sock_addr(sock):
    try:
        return sock.getpeername()
    except OSError: # socket already disconnected
        return "unknown"

def add_peer(peer_id, sock):
    with peers_lock:
        if peer_id in peers:
            return False
        peers[peer_id] = sock
        peer_files[peer_id] = []
    print(f"[peers] added {peer_id}")
    log_peer_change("added", peer_id, sock_addr(sock))
    return True

def remove_peer(peer_id, sock):
    with peers_lock:
        if peers.get(peer_id) is not sock: # already removed (or belongs to a different connection)
            return
        del peers[peer_id]
        del peer_files[peer_id]
    print(f"[peers] removed {peer_id}")
    log_peer_change("removed", peer_id, sock_addr(sock))

def send_msg(sock, msg):
    data = json.dumps(msg).encode() + b"\n" # using \n as the delimiter , } from previous may break it
    with send_lock:
        sock.sendall(data)
    log_msg(msg, True, sock_addr(sock))

def recv_msg(sock, buf):
    while b"\n" not in buf:   # continue reading if delimiter not found
        chunk = sock.recv(4096)
        if not chunk: # connection closed
            return None, buf
        buf += chunk
    line, buf = buf.split(b"\n", 1) # we have one full msg, but there may be extra bytes that we return to the buffer
    msg = json.loads(line)
    log_msg(msg, False, sock_addr(sock))
    return msg, buf
 
def make_file_list():
    os.makedirs(SHARED_DIR, exist_ok=True)
    files = sorted(f for f in os.listdir(SHARED_DIR) if os.path.isfile(os.path.join(SHARED_DIR, f))) # return all files in shared dir, sorted
    return {"type": "file_list", "node_id": NODE_ID, "files": files}
 
def handle_message(peer_id, sock, msg):
    msg_type = msg.get("type")
    if msg_type == "file_list": 
        files = msg.get("files", [])
        with peers_lock:                           
            if peer_id in peer_files:
                peer_files[peer_id] = files  
        print(f"[files] {peer_id} has {files}")
    else:
        # later: need to handle the other msgs
        print(f"[tcp] from {peer_id}: {msg}")

# peer will continue looping and wait  for request from other peer
def listen_to_peer(peer_id, sock, buf=b""):
    try:
        while True:
            msg, buf = recv_msg(sock, buf)
            if msg is None: # connection closed
                break
            handle_message(peer_id, sock, msg) # based on type of msg, act accordinly 
    except (OSError, ValueError):
        pass
    finally: # for any errors/closed connections we remove peer from our list
        remove_peer(peer_id, sock)
        sock.close()

 
def tcp_accept_loop(server):
    while True:
        conn, addr = server.accept()
        threading.Thread(target=setup_incoming_peer, args=(conn, addr), daemon=True).start()
 

def setup_incoming_peer(conn, addr):
    try:
        intro_msg, buf = recv_msg(conn, b"")
    except (OSError, ValueError):
        intro_msg, buf = None, b""

    if not intro_msg or intro_msg.get("type") != "file_list" or not intro_msg.get("node_id"):
        print(f"[tcp] {addr} did not identify itself, closing")
        conn.close()
        return

    peer_id = intro_msg["node_id"]
    add_to_peer = add_peer(peer_id, conn)
    if not add_to_peer:
        print(f"[tcp] already connected to {peer_id}, closing duplicate")
        conn.close()
        return
    print(f"[tcp] accepted {peer_id} from {addr}")

    handle_message(peer_id, conn, intro_msg) # store the file list it just sent
    try:
        send_msg(conn, make_file_list()) # reply with our own file list
    except OSError:
        pass
    listen_to_peer(peer_id, conn, buf) # thread loops to continue handling and receiving msg
    
# broadcast peer_request and collect peer_acks on start
def send_peer_request():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1) # enable broadcasting on this UDP socket

        msg = {"type": "peer_request", "node_id": NODE_ID}# protocol message for peer discovery
        sock.sendto(json.dumps(msg).encode(), (BROADCAST_ADDR, UDP_PORT))
        #log that we sent peer request
        print(f"[discovery] broadcasting peer_request")
        log_msg(msg, True, "BROADCAST")

        sock.settimeout(3)
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
            if ack.get("type") == "peer_ack" and ack.get("node_id") != NODE_ID:  # valid peer_ack from another node
                #log the peer ack receieved
                log_msg(ack, False, addr)
                peer_id = ack["node_id"]
                peer_addr = (addr[0], ack["tcp_port"]) # IP from the packet, port from the ACK
                print(f"[discovery] got peer_ack from {peer_addr}, id={peer_id}")

                if peer_id in peers: # already connected
                    continue
                tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # establish TCP
                tcp_sock.settimeout(5)                   
                try:
                    tcp_sock.connect(peer_addr)
                except OSError as e:
                    print(f"[tcp] could not connect to {peer_addr}: {e}")
                    tcp_sock.close()
                    continue
                tcp_sock.settimeout(None)       

                add_to_peer = add_peer(peer_id, tcp_sock) # adds the peer to the table
                if not add_to_peer: # if accept thread accepted a connection while this thread was running
                    tcp_sock.close()
                    continue
                print(f"[tcp] connected to {peer_id} at {peer_addr}")

                try:
                    send_msg(tcp_sock, make_file_list()) # we are client, send our file list to server
                except OSError: # if the connectoin dies while sending we still have to continue
                    pass                            
                threading.Thread(target=listen_to_peer, args=(peer_id, tcp_sock), daemon=True).start()        

                    


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

def start_tcp_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("", TCP_PORT)) # listen on any network
    server.listen()
    print(f"[tcp] listening on TCP {TCP_PORT}")
    threading.Thread(target=tcp_accept_loop, args=(server,), daemon=True).start() # start accepting messages


print(f"My id={NODE_ID}, tcp_port={TCP_PORT}")
start_tcp_server()
# listener first, so we're ready before we announce ourselves
threading.Thread(target=udp_listener, daemon=True).start()
send_peer_request()
while True:        
    time.sleep(1) # keep the main thread running (temporarily until final logic implemented)