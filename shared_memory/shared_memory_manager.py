import struct
import json
import time
from multiprocessing import shared_memory, Lock

BUFFER_SIZE = 1024 * 4  # 4 KB buffer
HEADER_SIZE = 8         # 4 bytes write_pos + 4 bytes read_pos

lock = Lock()

# Message header: msg_id (4 bytes), type_flag (1 byte), length (4 bytes)
MSG_HEADER_FMT = 'IbI'  # unsigned int, unsigned char, unsigned int
MSG_HEADER_SIZE = struct.calcsize(MSG_HEADER_FMT)


def init_shared_memory():
    try:
        shm = shared_memory.SharedMemory(create=True, size=BUFFER_SIZE, name='my_queue')
        with lock:
            struct.pack_into('II', shm.buf, 0, 0, 0)  # Initialize write_pos, read_pos
        print("[SharedMemory] Created")
    except FileExistsError:
        shm = shared_memory.SharedMemory(name='my_queue')
        print("[SharedMemory] Connected")
    return shm


def get_positions(buf):
    write_pos, read_pos = struct.unpack_from('II', buf, 0)
    return write_pos, read_pos


def set_positions(buf, write_pos, read_pos):
    struct.pack_into('II', buf, 0, write_pos, read_pos)


def available_space(write_pos, read_pos):
    if write_pos >= read_pos:
        return BUFFER_SIZE - HEADER_SIZE - (write_pos - read_pos)
    else:
        return read_pos - write_pos


def write_message(buf, msg_id, type_flag, message_json):
    data = message_json.encode('utf-8')
    length = len(data)
    total_len = MSG_HEADER_SIZE + length

    with lock:
        write_pos, read_pos = get_positions(buf)

        free_space = available_space(write_pos, read_pos)
        if total_len > free_space:
            raise BufferError("Not enough space in buffer")

        end_of_buffer = BUFFER_SIZE - HEADER_SIZE
        if write_pos + total_len <= end_of_buffer:
            # Write header
            struct.pack_into(MSG_HEADER_FMT, buf, HEADER_SIZE + write_pos, msg_id, type_flag, length)
            # Write data
            buf[HEADER_SIZE + write_pos + MSG_HEADER_SIZE : HEADER_SIZE + write_pos + MSG_HEADER_SIZE + length] = data
        else:
            # Wrap-around write
            first_part = end_of_buffer - write_pos
            if first_part < MSG_HEADER_SIZE:
                # Header wraps
                struct.pack_into(MSG_HEADER_FMT, buf, HEADER_SIZE, msg_id, type_flag, length)
                part1_len = 0
            else:
                struct.pack_into(MSG_HEADER_FMT, buf, HEADER_SIZE + write_pos, msg_id, type_flag, length)
                part1_len = MSG_HEADER_SIZE

            data_start = HEADER_SIZE + write_pos + part1_len
            part1_data_len = end_of_buffer - (write_pos + part1_len)
            buf[data_start:data_start+part1_data_len] = data[:part1_data_len]
            buf[HEADER_SIZE:HEADER_SIZE + (length - part1_data_len)] = data[part1_data_len:]

        new_write_pos = (write_pos + total_len) % (BUFFER_SIZE - HEADER_SIZE)
        set_positions(buf, new_write_pos, read_pos)


def read_message(buf, last_read_pos):
    with lock:
        write_pos, read_pos = get_positions(buf)
        if last_read_pos == write_pos:
            return None, last_read_pos  # No new message

        end_of_buffer = BUFFER_SIZE - HEADER_SIZE
        if last_read_pos + MSG_HEADER_SIZE <= end_of_buffer:
            msg_header = buf[HEADER_SIZE + last_read_pos : HEADER_SIZE + last_read_pos + MSG_HEADER_SIZE]
        else:
            part1_len = end_of_buffer - last_read_pos
            part1 = buf[HEADER_SIZE + last_read_pos : HEADER_SIZE + last_read_pos + part1_len]
            part2 = buf[HEADER_SIZE : HEADER_SIZE + (MSG_HEADER_SIZE - part1_len)]
            msg_header = part1 + part2

        msg_id, type_flag, length = struct.unpack(MSG_HEADER_FMT, msg_header)

        data_start = (last_read_pos + MSG_HEADER_SIZE) % (BUFFER_SIZE - HEADER_SIZE)
        if data_start + length <= end_of_buffer:
            data_bytes = buf[HEADER_SIZE + data_start : HEADER_SIZE + data_start + length]
        else:
            part1_len = end_of_buffer - data_start
            part1 = buf[HEADER_SIZE + data_start : HEADER_SIZE + data_start + part1_len]
            part2 = buf[HEADER_SIZE : HEADER_SIZE + (length - part1_len)]
            data_bytes = part1 + part2

        message_json = bytes(data_bytes).decode('utf-8')

        new_read_pos = (last_read_pos + MSG_HEADER_SIZE + length) % (BUFFER_SIZE - HEADER_SIZE)
        return (msg_id, type_flag, message_json), new_read_pos
