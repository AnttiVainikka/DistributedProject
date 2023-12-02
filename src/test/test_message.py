import socket, pickle
from messages.messages import *
from messages.message_processor import process_message

_host = 'localhost'
_port = 60000

def start_server():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((_host, _port))
    s.listen(1)

    print(f"Server is listening on {_host}:{_port}\n")
    while True:
        conn, addr = s.accept()
        print("Message received: ", end="")
        message_byte = conn.recv(4096)
        conn.close()
        
        message = pickle.loads(message_byte)
        print(message.__dict__ if hasattr(message, "__dict__") else message)
        if isinstance(message, str) and message == "stop":
            exit(0)
        else:
            process_message(message)
        print()

def _create_message(argv: list[str]):
    # I'm not doing any parse, this is just for test -> don't be stupid
    match argv[0]:
        case "-s" | "--stop":
            return StopMessage(int(argv[1]))
        
        case "-r" | "--resume":
            return ResumeMessage(int(argv[1]))
        
        case "-j" | "--jump_to_timestamp":
            return JumpToTimestampMessage(int(argv[1]), int(argv[2]))
        
        case _:
            raise ValueError(f"Unknown message type: {argv[0]}")

def send_message(argv: list[str]):
    message = _create_message(argv)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((_host, _port))
    message_byte = pickle.dumps(message)
    s.send(message_byte)
    print("Message has been sent")
    print(message.__dict__)
    s.close()

def stop_server():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((_host, _port))
    message_byte = pickle.dumps("stop")
    s.send(message_byte)
    s.close()
