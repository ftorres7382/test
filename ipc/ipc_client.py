from multiprocessing.connection import Client

address = ('./my_socket' if not __import__('os').name == 'nt' else r'\\.\pipe\my_named_pipe')

conn = Client(address, authkey=b'secret')
conn.send("Hello from client!")
response = conn.recv()
print("Server replied:", response)
conn.close()
