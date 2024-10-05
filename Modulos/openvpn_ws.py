#!/usr/bin/env python3
# encoding: utf-8
from websocket_server import WebsocketServer
import socket
import threading

# OpenVPN server details
OPENVPN_HOST = '127.0.0.1'
OPENVPN_PORT = 1194

# Create a new WebSocket server
ws_server = WebsocketServer(port=8080, host='0.0.0.0')

def forward_to_openvpn(ws_client, message):
    try:
        openvpn_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        openvpn_socket.connect((OPENVPN_HOST, OPENVPN_PORT))
        openvpn_socket.sendall(message.encode('utf-8'))  # Ensure message is encoded

        # Forward data from OpenVPN back to WebSocket
        while True:
            data = openvpn_socket.recv(4096)
            if not data:
                break
            ws_client.send_message(data.decode('utf-8'))  # Decode message for sending

        openvpn_socket.close()
    except Exception as e:
        print(f"Error: {e}")

# Called when a client sends a message
def message_received(client, server, message):
    threading.Thread(target=forward_to_openvpn, args=(client, message)).start()

# Start the WebSocket server
ws_server.set_fn_message_received(message_received)
ws_server.run_forever()
