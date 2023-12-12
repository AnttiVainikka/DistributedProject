from abc import ABC, abstractmethod
import log
import socket

IpAddress = str

_logger = log.getLogger(__name__)

class NetBackend(ABC):
    @abstractmethod
    def receive(self) -> tuple[IpAddress, str]:
        pass

    @abstractmethod
    def send(self, dest: IpAddress, data: str) -> None:
        pass

    @abstractmethod
    def shutdown(self) -> None:
        pass

class TcpBackend(NetBackend):
    """Quick and dirty networking."""
    server: socket.socket

    def __init__(self, port: int) -> None:
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind(('0.0.0.0', port))
        self.server.listen()
        self.server.settimeout(3)

    def receive(self) -> (IpAddress, str):
        # This can only receive from one peer at a time, hopefully that is fine
        try:
            conn, source = self.server.accept()
            data = bytearray()
            while True:
                frame = conn.recv(1000)
                _logger.info(f'Received frame of {len(frame)} bytes')
                if not frame:
                    break # Sender closed connection, which it will always do with our send(...)
                data.extend(frame)
            
            return (f'{source[0]}:{source[1]}', data.decode('utf-8'))
        except socket.timeout:
            return (None, None)

    def send(self, dest: IpAddress, data: str) -> bool:
        # Connect, send, close - inefficient, but easy
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.settimeout(1)
        _logger.info(f'Sending {len(data)} bytes to {dest}')
        parts = dest.split(':')
        try:
            client.connect((parts[0], int(parts[1])))
            client.sendall(data.encode('utf-8'))
            client.close()
        except socket.error:
            return False
        return True
    
    def shutdown(self) -> None:
        return
        self.server.shutdown(socket.SHUT_RDWR)