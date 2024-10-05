import socket, threading, select, signal, sys, time, argparse
from concurrent.futures import ThreadPoolExecutor

# CONFIG
LISTENING_ADDR = '0.0.0.0'
DEFAULT_PORT = 8880
PASS = ''

# CONST
BUFLEN = 4096 * 4
TIMEOUT = 60
DEFAULT_HOST = '127.0.0.1:1194'
RESPONSE = 'HTTP/1.1 101 Switching Protocols\r\n\r\n'
MAX_THREADS = 50  # Define maximum number of threads in the pool

class Server(threading.Thread):
    def __init__(self, host, port):
        threading.Thread.__init__(self)
        self.running = False
        self.host = host
        self.port = port
        self.threads = []
        self.threadsLock = threading.Lock()
        self.logLock = threading.Lock()
        self.pool = ThreadPoolExecutor(max_workers=MAX_THREADS)

    def run(self):
        self.soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.soc.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.soc.settimeout(2)
        intport = int(self.port)
        self.soc.bind((self.host, intport))
        self.soc.listen(0)
        self.running = True

        try:
            while self.running:
                try:
                    c, addr = self.soc.accept()
                    c.setblocking(1)
                    conn = ConnectionHandler(c, self, addr)
                    self.pool.submit(conn.run)
                    self.addConn(conn)
                except socket.timeout:
                    continue
        finally:
            self.running = False
            self.soc.close()
            self.pool.shutdown(wait=True)

    def printLog(self, log):
        with self.logLock:
            print(log)

    def addConn(self, conn):
        with self.threadsLock:
            if self.running:
                self.threads.append(conn)

    def removeConn(self, conn):
        with self.threadsLock:
            self.threads.remove(conn)

    def close(self):
        self.running = False
        with self.threadsLock:
            for c in self.threads:
                c.close()

class ConnectionHandler:
    def __init__(self, socClient, server, addr):
        self.clientClosed = False
        self.targetClosed = True
        self.client = socClient
        self.client_buffer = ''
        self.server = server
        self.log = 'Connection: ' + str(addr)

    def close(self):
        try:
            if not self.clientClosed:
                self.client.shutdown(socket.SHUT_RDWR)
                self.client.close()
        except:
            pass
        finally:
            self.clientClosed = True

        try:
            if not self.targetClosed:
                self.target.shutdown(socket.SHUT_RDWR)
                self.target.close()
        except:
            pass
        finally:
            self.targetClosed = True

    def run(self):
        try:
            self.client_buffer = self.client.recv(BUFLEN)

            hostPort = self.findHeader(self.client_buffer, 'X-Real-Host')

            if not hostPort:
                hostPort = DEFAULT_HOST

            split = self.findHeader(self.client_buffer, 'X-Split')
            if split:
                self.client.recv(BUFLEN)

            if hostPort:
                passwd = self.findHeader(self.client_buffer, 'X-Pass')

                if PASS and passwd == PASS:
                    self.method_CONNECT(hostPort)
                elif PASS and passwd != PASS:
                    self.client.send(b'HTTP/1.1 400 WrongPass!\r\n\r\n')
                elif hostPort.startswith('127.0.0.1') or hostPort.startswith('localhost'):
                    self.method_CONNECT(hostPort)
                else:
                    self.client.send(b'HTTP/1.1 403 Forbidden!\r\n\r\n')
            else:
                self.server.printLog('- No X-Real-Host!')
                self.client.send(b'HTTP/1.1 400 NoXRealHost!\r\n\r\n')

        except Exception as e:
            self.log += f' - error: {str(e)}'
            self.server.printLog(self.log)
        finally:
            self.close()
            self.server.removeConn(self)

    def findHeader(self, head, header):
        aux = head.find(f'{header}: ')
        if aux == -1:
            return ''
        aux = head.find(':', aux)
        head = head[aux+2:]
        aux = head.find('\r\n')
        if aux == -1:
            return ''
        return head[:aux]

    def connect_target(self, host):
        i = host.find(':')
        if i != -1:
            port = int(host[i+1:])
            host = host[:i]
        else:
            port = 443 if self.method == 'CONNECT' else DEFAULT_PORT

        (soc_family, soc_type, proto, _, address) = socket.getaddrinfo(host, port)[0]
        self.target = socket.socket(soc_family, soc_type, proto)
        self.targetClosed = False
        self.target.connect(address)

    def method_CONNECT(self, path):
        self.log += f' - CONNECT {path}'
        self.connect_target(path)
        self.client.sendall(RESPONSE.encode())
        self.client_buffer = ''
        self.server.printLog(self.log)
        self.doCONNECT()

    def doCONNECT(self):
        socs = [self.client, self.target]
        count = 0
        error = False
        while True:
            count += 1
            recv, _, err = select.select(socs, [], socs, 3)
            if err:
                error = True
            if recv:
                for in_ in recv:
                    try:
                        data = in_.recv(BUFLEN)
                        if data:
                            if in_ is self.target:
                                self.client.sendall(data)
                            else:
                                self.target.sendall(data)
                            count = 0
                        else:
                            error = True
                    except:
                        error = True
                        break
            if count == TIMEOUT or error:
                break

def parse_args():
    parser = argparse.ArgumentParser(description='Python Proxy Server')
    parser.add_argument('-b', '--bind', default=LISTENING_ADDR, help='Bind address')
    parser.add_argument('-p', '--port', type=int, default=DEFAULT_PORT, help='Port to listen on')
    return parser.parse_args()

def main():
    args = parse_args()
    print("\n:-------PythonProxy-------:\n")
    print(f"Listening addr: {args.bind}")
    print(f"Listening port: {args.port}\n")
    print(":-------------------------:\n")

    server = Server(args.bind, args.port)
    server.start()

    try:
        while True:
            time.sleep(2)
    except KeyboardInterrupt:
        print('Stopping...')
        server.close()

if __name__ == '__main__':
    main()
