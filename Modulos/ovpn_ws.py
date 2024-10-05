#!/usr/bin/python3

import socket, threading, select

# Configuration
LISTENING_ADDR = '0.0.0.0'
LISTENING_PORT = 8880
PASS = ''  # Password for authentication, leave empty if no password is required
BUFLEN = 8196 * 8
TIMEOUT_HELLO = 3
DEFAULT_HOST = '0.0.0.0:1194'

# Colors for terminal output
RED = '\033[91m'
GREEN = '\033[92m'
ENDC = '\033[0m'

class Server:
    def __init__(self, host, port):
        self.bind_addr = (host, port)
        self.running = True
        self.connections = []

    def start(self):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind(self.bind_addr)
        self.server.listen(10)
        print(GREEN + f'[INFO] Listening on {self.bind_addr[0]}:{self.bind_addr[1]}' + ENDC)

        while self.running:
            try:
                conn, addr = self.server.accept()
                self.connections.append(conn)
                print(GREEN + f'[INFO] New connection from {addr}' + ENDC)
                ConnectionHandler(self, conn, addr).start()
            except Exception as e:
                print(RED + f'[ERROR] Error accepting connection: {e}' + ENDC)

    def removeConn(self, conn):
        if conn in self.connections:
            self.connections.remove(conn)

    def printLog(self, log):
        print(log)

class ConnectionHandler(threading.Thread):
    def __init__(self, server, conn, addr):
        super().__init__()
        self.server = server
        self.client = conn
        self.client_addr = addr
        self.client_buffer = b''
        self.log = f"[{self.client_addr}] "

    def findHeader(self, headers, name):
        try:
            header_line = next(line for line in headers.decode().splitlines() if line.startswith(name))
            return header_line.split(": ")[1]
        except StopIteration:
            return ''

    def run(self):
        try:
            self.client.settimeout(TIMEOUT_HELLO)
            self.client_buffer = self.client.recv(BUFLEN)
            print(f"[INFO] Received data from client {self.client_addr}: {self.client_buffer[:50]}")  # Log first 50 bytes
            hostPort = self.findHeader(self.client_buffer, 'X-Real-Host')

            if hostPort == '':
                hostPort = DEFAULT_HOST

            split = self.findHeader(self.client_buffer, 'X-Split')

            if split != '':
                self.client.recv(BUFLEN)

            if hostPort != '':
                passwd = self.findHeader(self.client_buffer, 'X-Pass')

                if len(PASS) != 0 and passwd == PASS:
                    self.method_CONNECT(hostPort)
                elif len(PASS) != 0 and passwd != PASS:
                    self.client.send(b'HTTP/1.1 400 WrongPass!\r\n\r\n')
                    print(RED + '[ERROR] Wrong password!' + ENDC)
                elif hostPort.startswith('127.0.0.1') or hostPort.startswith('localhost'):
                    self.method_CONNECT(hostPort)
                else:
                    self.client.send(b'HTTP/1.1 403 Forbidden!\r\n\r\n')
                    print(RED + f'[ERROR] Forbidden connection attempt to {hostPort}' + ENDC)
            else:
                print(RED + '[ERROR] No X-Real-Host header received!' + ENDC)
                self.client.send(b'HTTP/1.1 400 NoXRealHost!\r\n\r\n')

        except Exception as e:
            print(RED + f'[ERROR] Connection error: {e}' + ENDC)
        finally:
            self.close()

    def method_CONNECT(self, hostPort):
        try:
            self.log += f'Connecting to {hostPort}...'
            print(self.log)

            host, port = hostPort.split(':')
            port = int(port)

            remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            remote.connect((host, port))

            self.client.send(b'HTTP/1.1 200 Connection Established\r\n\r\n')
            self.server.printLog(self.log + 'Connection established.')

            self.client.settimeout(None)
            remote.settimeout(None)

            self.handle_tunnel(self.client, remote)

        except Exception as e:
            print(RED + f'[ERROR] Failed to connect to {hostPort}: {e}' + ENDC)

    def handle_tunnel(self, client, remote):
        try:
            while True:
                ready_sockets, _, _ = select.select([client, remote], [], [])
                if client in ready_sockets:
                    data = client.recv(BUFLEN)
                    if len(data) == 0:
                        break
                    remote.send(data)

                if remote in ready_sockets:
                    data = remote.recv(BUFLEN)
                    if len(data) == 0:
                        break
                    client.send(data)
        except Exception as e:
            print(RED + f'[ERROR] Error in data forwarding: {e}' + ENDC)

    def close(self):
        try:
            self.client.close()
        except Exception as e:
            print(RED + f'[ERROR] Error closing client connection: {e}' + ENDC)
        self.server.removeConn(self)

if __name__ == '__main__':
    try:
        print(GREEN + ':-------PythonProxy-------:' + ENDC)
        print(f'Listening addr: {LISTENING_ADDR}')
        print(f'Listening port: {LISTENING_PORT}')
        print(GREEN + ':-------------------------:' + ENDC)

        server = Server(LISTENING_ADDR, LISTENING_PORT)
        server.start()
    except Exception as e:
        print(RED + f'[ERROR] Server startup failed: {e}' + ENDC)
