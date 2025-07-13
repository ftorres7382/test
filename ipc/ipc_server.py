from multiprocessing.connection import Listener

address = ('./my_socket' if not __import__('os').name == 'nt' else r'\\.\pipe\my_named_pipe')

listener = Listener(address, authkey=b'secret')

print("Server started.")
while True:
    conn = listener.accept()
    print("Connection accepted.")
    msg = conn.recv()
    print(f"Received: {msg}")
    conn.send(f"Echo: {msg}")
    conn.close()
