# PA2: P2P File Share

## How to Run

```
python3 agent.py [tcp_port]
```

`tcp_port` is optional (default 12345). To run several nodes on one machine, give each its own port (`6001`, `6002`, ...). Test on a home router or hotspot, not campus Wi-Fi.

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
{
  "type": "file_list",
  "node_id": "5b1dc793",
  "files": ["alice.txt", "photo.jpg"]
}

{
  "type": "data_request",
  "node_id": "5b1dc793",
  "file_name": "Project Hail Mary.txt"
}

{
  "type": "file_data",
  "node_id": "5b1dc793",
  "file_name": "Project Hail Mary.txt",
  "file": "'IldoYXQncyB0d28gcGx1cyB0d28/" //Some base64 bytestream string
}

{
  "type": "file_error",
  "node_id": "5b1dc793",
  "error_message": "5c36eb78 no longer has Project Hail Mary.txt",
  "file_name": "Project Hail Mary.txt"
}
```
