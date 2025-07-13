import time
from shared_memory_manager import init_shared_memory, read_message, write_message


def client_process(client_id, message):
    shm = init_shared_memory()
    my_msg_id = client_id  # Unique ID per client

    try:
        write_message(shm.buf, my_msg_id, 0, message)
        print(f"[Client {client_id}] Request sent: {message}")
    except BufferError:
        print(f"[Client {client_id}] Buffer full, cannot send request")
        return

    read_pos = 0
    while True:
        result = read_message(shm.buf, read_pos)
        if result is None:
            time.sleep(0.1)
            continue

        (msg_id, type_flag, msg), read_pos = result

        if msg_id == my_msg_id and type_flag == 1:
            print(f"[Client {client_id}] Response received: {msg}")
            break


if __name__ == "__main__":
    import sys

    client_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    message = sys.argv[2] if len(sys.argv) > 2 else f"Hello from client {client_id}!"

    client_process(client_id, message)
