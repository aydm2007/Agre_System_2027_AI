import socket

def check_port(host, port, timeout=2):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        if result == 0:
            print(f"Port {port} is OPEN")
        else:
            print(f"Port {port} is CLOSED or Unreachable")
        sock.close()
    except Exception as e:
        print(f"Error checking port: {e}")

check_port('127.0.0.1', 5432)
check_port('127.0.0.1', 8000)
check_port('127.0.0.1', 5173)
