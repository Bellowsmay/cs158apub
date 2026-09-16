"""
UDP Echo Client
---------------
Sends datagrams to the UDP echo server and prints the response.
Type 'quit' to exit.

Run:
    python udp_client.py

Make sure udp_server.py is already running first.
"""

import socket

##HOST = "127.0.0.1"  # server address
HOST = "192.168.1.2."
PORT = 65433        # must match udp_server.py
BUFFER_SIZE = 1024
TIMEOUT = 2         # seconds to wait for a reply before giving up

# SOCK_DGRAM = UDP socket — no connect() call needed.
with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:

    # settimeout() makes recvfrom() raise socket.timeout instead of
    # blocking forever if the server is down or the packet is lost.
    sock.settimeout(TIMEOUT)

    print(f"[UDP Client] Ready to send to {HOST}:{PORT}")
    print("[UDP Client] Type a message and press Enter. Type 'quit' to exit.\n")

    while True:
        message = input("You: ").strip()

        if message.lower() == "quit":
            print("[UDP Client] Goodbye.")
            break

        if not message:
            continue

        # sendto() sends one datagram to the server.
        # Unlike TCP, there is no handshake — the packet just goes out.
        sock.sendto(message.encode(), (HOST, PORT))

        try:
            # recvfrom() waits up to TIMEOUT seconds for the server's reply.
            response, server_addr = sock.recvfrom(BUFFER_SIZE)
            print(f"Echo: {response.decode()}\n")

        except TimeoutError:
            # The datagram may have been lost, or the server may be down.
            print("[UDP Client] No response — packet lost or server unreachable.\n")
