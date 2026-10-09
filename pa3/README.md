# PA2: P2P File Share

## How to Run

```
python3 agent.py [tcp_port]
```

`tcp_port` is optional (default 12345). To run several nodes on one machine, give each its own port (`6001`, `6002`, ...). Test on a home router or hotspot, not campus Wi-Fi.

## Peer Discovery (UDP, port 54321)

On startup a node broadcasts a `peer_request` to `255.255.255.255:54321`, then collects `peer_ack` replies until 3 seconds pass with no new one. A listener thread stays bound to port 54321 for the node's lifetime and answers every `peer_request` from another node.

Each UDP message is one JSON object (UTF-8). No length prefix is needed since a UDP datagram is exactly one message. The `type` field identifies it.

| type | fields |
|---|---|
| `peer_request` | `node_id` |
| `peer_ack` | `node_id`, `tcp_port` |

```json
{"type": "peer_request", "node_id": "5b1dc793"}
{"type": "peer_ack", "node_id": "8b18a437", "tcp_port": 6001}
```

The peer's IP is taken from the UDP packet's source address. `node_id` is a random 8-char hex string, used to ignore a node's own broadcasts.