import time
import json
from shared_memory_manager import init_shared_memory, read_message, write_message


def server_process():
    shm = init_shared_memory()
    read_pos = 0

    print("[Server] Running")
    while True:
        result = read_message(shm.buf, read_pos)
        if result is None:
            time.sleep(0.1)
            continue

        (msg_id, type_flag, msg), read_pos = result

        if type_flag == 0:  # Request
            print(f"[Server] Request ID {msg_id} received: {msg}")
            # Example processing: reverse string in JSON
            response = json.dumps({"response": msg[::-1]})

            try:
                write_message(shm.buf, msg_id, 1, response)
                print(f"[Server] Response ID {msg_id} sent")
            except BufferError:
                print("[Server] Buffer full, cannot send response")


if __name__ == "__main__":
    server_process()
