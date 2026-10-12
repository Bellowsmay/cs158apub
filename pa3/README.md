# PA2: P2P File Share

## Contributions:
UDP Layer - Luan Nguyen
TCP Layer - Sai Wong
File Transfer - Alex Lim

## How to Run

```
cd pa3
python3 agent.py [tcp_port]
```

`tcp_port` is optional (default 12345). To run several nodes on one machine, give each its own port (`6001`, `6002`, ...). Test on a home router or hotspot, not campus Wi-Fi.

## How to - Transfering Files
1. To start a file transfer, make sure the nodes have files to transfer in the corresponding shared directories.
2. Delete any and all download folders. They will be created by the program, but not emptied by it.
3. Upon receiving a file list from a peer node, the current node will be prompted to enter the name of a singular file to receive from that list. Users will ONLY receive the prompt if they DO NOT HAVE a file in that list. If they have all the files, they will not be prompted.
- NOTE: Other printed statements may appear after the user is prompted. THIS IS FINE. Continue to enter the file name like normal. 
![alt text](<Prompt Example.png>)
4. Repeat step 2 until all prompts are answered, all files are recived, or all other peer nodes are terminated.

Technology Info:
For file data, the message format is JSON, but the file data field is encoded into a base64 byte string. We chose this method for simplicity. Otherwise we would need to specify byte length at the beginning of the message.
Messages are delimited with \n.

## Peer Discovery (UDP, port 54321)

On startup a node broadcasts a `peer_request` to `255.255.255.255:54321`, then collects `peer_ack` replies until 3 seconds pass with no new one. A listener thread stays bound to port 54321 for the node's lifetime and answers every `peer_request` from another node.

Each UDP message is one JSON object (UTF-8). No length prefix is needed since a UDP datagram is exactly one message. The `type` field identifies it.

| type           | fields                |
| -------------- | --------------------- |
| `peer_request` | `node_id`             |
| `peer_ack`     | `node_id`, `tcp_port` |

```json
{"type": "peer_request", "node_id": "5b1dc793"}
{"type": "peer_ack", "node_id": "8b18a437", "tcp_port": 6001}
```

The peer's IP is taken from the UDP packet's source address. `node_id` is a random 8-char hex string, used to ignore a node's own broadcasts.

## Peer Connection (TCP)

The node that sent the `peer_request` is the TCP client: after a `peer_ack`, it connects to the ack's source IP and `tcp_port`. The node that sent the ack is the TCP server and accepts on its `tcp_port`.

Each node keeps a peer table mapping `node_id` to that peer's socket. Before connecting, and again when registering a new connection, a node checks this table and closes the new connection if the peer is already connected, so each pair has exactly one connection.

The first message on a new TCP connection, in both directions, is a `file_list`. Its `node_id` field is how the accepting side learns who connected; a connection whose first message is not a `file_list` with a `node_id` is closed.

## TCP Message Format

Every TCP message is one JSON object (UTF-8) followed by a newline (`\n`). The receiver reads bytes into a buffer until it contains a `\n`, takes everything before it as one message, and keeps the remainder for the next message. This handles a single `recv` returning part of a message or several messages at once.

| type           | fields                                     |
| -------------- | -------------------------------------------|
| `file_list`    | `node_id`, `files`                         |
| `data_request` | `node_id`, `file_name`                     |
| `file_data`    | `node_id`, `file_name`, `file`             |
| `file_error`   | `node_id`, `error_message`, `file_name`    |

```json
Used to advertise files to peers
{
  "type": "file_list",
  "node_id": "5b1dc793",
  "files": ["alice.txt", "photo.jpg"]
}

Used to request a file from a peer
{
  "type": "data_request",
  "node_id": "5b1dc793",
  "file_name": "Project Hail Mary.txt"
}

Used to send actual file contents to peers
Note: For file data, the message format is JSON, but the file data field is encoded into a base64 byte string.
{
  "type": "file_data",
  "node_id": "5b1dc793",
  "file_name": "Project Hail Mary.txt",
  "file": "'IldoYXQncyB0d28gcGx1cyB0d28/" 
}

Used to explain why file could not be sent
{
  "type": "file_error",
  "node_id": "5b1dc793",
  "error_message": "5c36eb78 no longer has Project Hail Mary.txt",
  "file_name": "Project Hail Mary.txt"
}
```
-------------------------------Execution Example of Agent5.py-----------------------------------------
PS C:\Users\alima\OneDrive\Documents\GitHub\cs158apub> cd pa3
PS C:\Users\alima\OneDrive\Documents\GitHub\cs158apub\pa3> python agent5.py 6005 
My id=a653c127, tcp_port=6005
[tcp] listening on TCP 6005

[listener] listening on UDP 54321

[listener] ignored my own broadcast
[discovery] broadcasting peer_request

[discovery] got peer_ack from ('192.168.56.1', 6001), id=26ceb384
[peers] added 26ceb384
[tcp] connected to 26ceb384 at ('192.168.56.1', 6001)
[discovery] got peer_ack from ('192.168.56.1', 54322), id=9a01648d
[peers] added 9a01648d
[tcp] connected to 9a01648d at ('192.168.56.1', 54322)
[discovery] got peer_ack from ('192.168.56.1', 6004), id=1ae26e17
[peers] added 1ae26e17
[tcp] connected to 1ae26e17 at ('192.168.56.1', 6004)
[discovery] got peer_ack from ('192.168.56.1', 6003), id=2ae06e2d
[peers] added 2ae06e2d
[tcp] connected to 2ae06e2d at ('192.168.56.1', 6003)
[discovery] no peer_acks received, done waiting
[file list] Available files from 26ceb384: ['End Poem.txt']
-------------WHICH FILE WOULD YOU LIKE TO REQUEST FROM 26ceb384? (Enter 'none' for none)-------------
End Poem.txt
[file list] Available files from 9a01648d: ['Project Hail Mary.txt']
-------------WHICH FILE WOULD YOU LIKE TO REQUEST FROM 9a01648d? (Enter 'none' for none)-------------
[Transfer] End Poem.txt to shared folder
Project Hail Mary.txt
[file list] Available files from 1ae26e17: ['Ocarina.txt']
-------------WHICH FILE WOULD YOU LIKE TO REQUEST FROM 1ae26e17? (Enter 'none' for none)-------------
[Transfer] Project Hail Mary.txt to shared folder
Ocarina.txt
[file list] Available files from 2ae06e2d: ['Nothing Gold Can Stay.txt']
-------------WHICH FILE WOULD YOU LIKE TO REQUEST FROM 2ae06e2d? (Enter 'none' for none)-------------
[Transfer] Ocarina.txt to shared folder
Nothing Gold Can Stay.txt
[Transfer] Nothing Gold Can Stay.txt to shared folder


-------------------------------Execution Example of Agent4.py-----------------------------------------
PS C:\Users\alima\OneDrive\Documents\GitHub\cs158apub> cd pa3
PS C:\Users\alima\OneDrive\Documents\GitHub\cs158apub\pa3> python agent4.py 6004 
My id=1ae26e17, tcp_port=6004
[tcp] listening on TCP 6004

[listener] listening on UDP 54321

[listener] ignored my own broadcast
[discovery] broadcasting peer_request

[discovery] got peer_ack from ('192.168.56.1', 54322), id=9a01648d
[peers] added 9a01648d
[tcp] connected to 9a01648d at ('192.168.56.1', 54322)
[discovery] got peer_ack from ('192.168.56.1', 6003), id=2ae06e2d
[peers] added 2ae06e2d
[tcp] connected to 2ae06e2d at ('192.168.56.1', 6003)
[discovery] got peer_ack from ('192.168.56.1', 6001), id=26ceb384
[peers] added 26ceb384
[tcp] connected to 26ceb384 at ('192.168.56.1', 6001)
[listener] got peer_request from ('192.168.56.1', 64304), id=a653c127
[listener] sent peer_ack to ('192.168.56.1', 64304), node_id=1ae26e17
[peers] added a653c127
[tcp] accepted a653c127 from ('192.168.56.1', 59538)
[discovery] no peer_acks received, done waiting
[file list] Available files from 9a01648d: ['Project Hail Mary.txt']
-------------WHICH FILE WOULD YOU LIKE TO REQUEST FROM 9a01648d? (Enter 'none' for none)-------------
Project Hail Mary.txt
[file list] Available files from 2ae06e2d: ['Nothing Gold Can Stay.txt']
-------------WHICH FILE WOULD YOU LIKE TO REQUEST FROM 2ae06e2d? (Enter 'none' for none)-------------
[Transfer] Project Hail Mary.txt to shared folder
Nothing Gold Can Stay.txt
[file list] Available files from 26ceb384: ['End Poem.txt']
-------------WHICH FILE WOULD YOU LIKE TO REQUEST FROM 26ceb384? (Enter 'none' for none)-------------
[Transfer] Nothing Gold Can Stay.txt to shared folder
End Poem.txt
[file list] Available files from a653c127: ['End Poem.txt', 'PA3 Overview.txt']
-------------WHICH FILE WOULD YOU LIKE TO REQUEST FROM a653c127? (Enter 'none' for none)-------------
[Transfer] End Poem.txt to shared folder
PA3 Overview.txt
[Transfer] PA3 Overview.txt to shared folder
[peers] removed a653c127


-------------------------------Execution Example of Agent3.py-----------------------------------------
PS C:\Users\alima\OneDrive\Documents\GitHub\cs158apub> cd pa3
PS C:\Users\alima\OneDrive\Documents\GitHub\cs158apub\pa3> python agent3.py 6003 
My id=2ae06e2d, tcp_port=6003
[tcp] listening on TCP 6003

[listener] listening on UDP 54321

[listener] ignored my own broadcast
[discovery] broadcasting peer_request

[discovery] got peer_ack from ('192.168.56.1', 54322), id=9a01648d
[peers] added 9a01648d
[tcp] connected to 9a01648d at ('192.168.56.1', 54322)
[discovery] got peer_ack from ('192.168.56.1', 6001), id=26ceb384
[peers] added 26ceb384
[tcp] connected to 26ceb384 at ('192.168.56.1', 6001)
[listener] got peer_request from ('192.168.56.1', 64303), id=1ae26e17
[listener] sent peer_ack to ('192.168.56.1', 64303), node_id=2ae06e2d
[peers] added 1ae26e17
[tcp] accepted 1ae26e17 from ('192.168.56.1', 59527)
[discovery] no peer_acks received, done waiting
[file list] Available files from 9a01648d: ['Project Hail Mary.txt']
-------------WHICH FILE WOULD YOU LIKE TO REQUEST FROM 9a01648d? (Enter 'none' for none)-------------
[listener] got peer_request from ('192.168.56.1', 64304), id=a653c127
[listener] sent peer_ack to ('192.168.56.1', 64304), node_id=2ae06e2d
[peers] added a653c127
[tcp] accepted a653c127 from ('192.168.56.1', 59539)
Project Hail Mary.txt
[file list] Available files from 26ceb384: ['End Poem.txt']
-------------WHICH FILE WOULD YOU LIKE TO REQUEST FROM 26ceb384? (Enter 'none' for none)-------------
[Transfer] Project Hail Mary.txt to shared folder
End Poem.txt
[file list] Available files from 1ae26e17: ['End Poem.txt', 'Ocarina.txt', 'PA3 Overview.txt']
-------------WHICH FILE WOULD YOU LIKE TO REQUEST FROM 1ae26e17? (Enter 'none' for none)-------------
[Transfer] End Poem.txt to shared folder
Ocarina.txt
[file list] Available files from 1ae26e17: ['PA3 Overview.txt']
-------------WHICH FILE WOULD YOU LIKE TO REQUEST FROM 1ae26e17? (Enter 'none' for none)-------------
[Transfer] Ocarina.txt to shared folder
PA3 Overview.txt
[file list] Available files from a653c127: ['PA3 Overview.txt']
-------------WHICH FILE WOULD YOU LIKE TO REQUEST FROM a653c127? (Enter 'none' for none)-------------
[Transfer] PA3 Overview.txt to shared folder
PA3 Overview.txt
[Transfer] Skipped PA3 Overview.txt. Already exists in downloads
[peers] removed a653c127

[peers] removed 1ae26e17


-------------------------------Execution Example of Agent2.py-----------------------------------------
PS C:\Users\alima\OneDrive\Documents\GitHub\cs158apub> cd pa3
PS C:\Users\alima\OneDrive\Documents\GitHub\cs158apub\pa3> python agent2.py 54322
My id=9a01648d, tcp_port=54322
[tcp] listening on TCP 54322

[listener] listening on UDP 54321

[discovery] broadcasting peer_request

[listener] ignored my own broadcast
[discovery] got peer_ack from ('192.168.56.1', 6001), id=26ceb384
[peers] added 26ceb384
[tcp] connected to 26ceb384 at ('192.168.56.1', 6001)
[listener] got peer_request from ('192.168.56.1', 63864), id=2ae06e2d
[listener] sent peer_ack to ('192.168.56.1', 63864), node_id=9a01648d
[peers] added 2ae06e2d
[tcp] accepted 2ae06e2d from ('192.168.56.1', 59499)
[discovery] no peer_acks received, done waiting
[file list] Available files from 26ceb384: ['End Poem.txt']
-------------WHICH FILE WOULD YOU LIKE TO REQUEST FROM 26ceb384? (Enter 'none' for none)-------------
[listener] got peer_request from ('192.168.56.1', 64303), id=1ae26e17
[listener] sent peer_ack to ('192.168.56.1', 64303), node_id=9a01648d
[peers] added 1ae26e17
[tcp] accepted 1ae26e17 from ('192.168.56.1', 59526)
[listener] got peer_request from ('192.168.56.1', 64304), id=a653c127
[listener] sent peer_ack to ('192.168.56.1', 64304), node_id=9a01648d
[peers] added a653c127
[tcp] accepted a653c127 from ('192.168.56.1', 59537)
End Poem.txt
[file list] Available files from 2ae06e2d: ['End Poem.txt', 'Nothing Gold Can Stay.txt', 'Ocarina.txt', 'PA3 Overview.txt']
-------------WHICH FILE WOULD YOU LIKE TO REQUEST FROM 2ae06e2d? (Enter 'none' for none)-------------
[Transfer] End Poem.txt to shared folder
Nothing Gold Can Stay.txt
[file list] Available files from 2ae06e2d: ['Ocarina.txt', 'PA3 Overview.txt']
-------------WHICH FILE WOULD YOU LIKE TO REQUEST FROM 2ae06e2d? (Enter 'none' for none)-------------
[Transfer] Nothing Gold Can Stay.txt to shared folder
Ocarina.txt
[file list] Available files from 1ae26e17: ['Ocarina.txt', 'PA3 Overview.txt']
-------------WHICH FILE WOULD YOU LIKE TO REQUEST FROM 1ae26e17? (Enter 'none' for none)-------------
[Transfer] Ocarina.txt to shared folder
PA3 Overview.txt
[file list] Available files from a653c127: ['PA3 Overview.txt']
-------------WHICH FILE WOULD YOU LIKE TO REQUEST FROM a653c127? (Enter 'none' for none)-------------
[Transfer] PA3 Overview.txt to shared folder
none
[peers] removed a653c127

[peers] removed 1ae26e17

[peers] removed 2ae06e2d

-------------------------------Execution Example of Agent.py-----------------------------------------
PS C:\Users\alima\OneDrive\Documents\GitHub\cs158apub> cd pa3                
PS C:\Users\alima\OneDrive\Documents\GitHub\cs158apub\pa3> python agent.py 6001  
My id=26ceb384, tcp_port=6001
[tcp] listening on TCP 6001

[listener] listening on UDP 54321

[listener] ignored my own broadcast
[discovery] broadcasting peer_request

[listener] got peer_request from ('192.168.56.1', 63863), id=9a01648d
[listener] sent peer_ack to ('192.168.56.1', 63863), node_id=26ceb384
[peers] added 9a01648d
[tcp] accepted 9a01648d from ('192.168.56.1', 59478)
[listener] got peer_request from ('192.168.56.1', 63864), id=2ae06e2d
[listener] sent peer_ack to ('192.168.56.1', 63864), node_id=26ceb384
[peers] added 2ae06e2d
[tcp] accepted 2ae06e2d from ('192.168.56.1', 59500)
[discovery] no peer_acks received, done waiting
[file list] Available files from 9a01648d: ['Project Hail Mary.txt']
-------------WHICH FILE WOULD YOU LIKE TO REQUEST FROM 9a01648d? (Enter 'none' for none)-------------
[listener] got peer_request from ('192.168.56.1', 64303), id=1ae26e17
[listener] sent peer_ack to ('192.168.56.1', 64303), node_id=26ceb384
[peers] added 1ae26e17
[tcp] accepted 1ae26e17 from ('192.168.56.1', 59529)
[listener] got peer_request from ('192.168.56.1', 64304), id=a653c127
[listener] sent peer_ack to ('192.168.56.1', 64304), node_id=26ceb384
[peers] added a653c127
[tcp] accepted a653c127 from ('192.168.56.1', 59536)
Project Hail Mary.txt
[file list] Available files from 2ae06e2d: ['Nothing Gold Can Stay.txt', 'Ocarina.txt', 'PA3 Overview.txt', 'Project Hail Mary.txt']
-------------WHICH FILE WOULD YOU LIKE TO REQUEST FROM 2ae06e2d? (Enter 'none' for none)-------------
[Transfer] Project Hail Mary.txt to shared folder
Nothing Gold Can Stay.txt
[file list] Available files from 9a01648d: ['Nothing Gold Can Stay.txt', 'Ocarina.txt', 'PA3 Overview.txt']
-------------WHICH FILE WOULD YOU LIKE TO REQUEST FROM 9a01648d? (Enter 'none' for none)-------------
[Transfer] Nothing Gold Can Stay.txt to shared folder
Ocarina.txt
[file list] Available files from 2ae06e2d: ['Ocarina.txt', 'PA3 Overview.txt']
-------------WHICH FILE WOULD YOU LIKE TO REQUEST FROM 2ae06e2d? (Enter 'none' for none)-------------
[Transfer] Ocarina.txt to shared folder
PA3 Overview.txt
[file list] Available files from 1ae26e17: ['PA3 Overview.txt']
-------------WHICH FILE WOULD YOU LIKE TO REQUEST FROM 1ae26e17? (Enter 'none' for none)-------------
[Transfer] PA3 Overview.txt to shared folder
PA3 Overview.txt
[Transfer] Skipped PA3 Overview.txt. Already exists in downloads
[peers] removed a653c127

[peers] removed 1ae26e17

[peers] removed 2ae06e2d

[peers] removed 9a01648d