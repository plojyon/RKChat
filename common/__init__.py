import time
import struct
import datetime
import re

PORT = 1234
TYPE = {"public": 0, "private": 1, "error": 2, "username": 3}
ERRORS = {"invalid_username": 1, "banned": 2}


def receive_fixed_length_msg(sock, msglen):
    message = b""
    while len(message) < msglen:
        chunk = sock.recv(msglen - len(message))  # preberi nekaj bajtov
        if chunk == b"":
            raise RuntimeError("socket connection broken")
        message = message + chunk  # pripni prebrane bajte sporocilu

    return message


def receive_message(sock):
    # read header H=2,I=4,B=1
    header = receive_fixed_length_msg(sock, 2 + 4 + 1)
    header_fields = struct.unpack("<HIB", header)

    # H = type | msg_len
    type = header_fields[0] >> (2 * 8 - 2)
    msg_len = header_fields[0] & 0b0011111111111111

    timestamp = header_fields[1]  # I = timestamp
    code = header_fields[2]  # B = code

    message = None
    if msg_len > 0:
        message = receive_fixed_length_msg(sock, msg_len)
        message = message.decode("utf-8")

    username = None
    if type != TYPE["error"] and code > 0:
        username = receive_fixed_length_msg(sock, code)
        username = username.decode("utf-8")

    return {
        "type": type,
        "timestamp": timestamp,
        "code": code,
        "message": message,
        "username": username,
    }


def encode_message(message="", type=TYPE["public"], user="", code=None):
    encoded_message = message.encode("utf-8")
    user = user.encode("utf-8")

    if len(encoded_message) >= 1 << 14:
        raise ValueError("Message too long")
    if len("{0:b}".format(type)) >= 1 << 2:
        raise ValueError("Invalid message type")
    if len(user) >= 1 << 8:
        raise ValueError("Username too long")

    msglen = len(encoded_message)
    # type_mask = 0b11000000 00000000
    # leng_mask = 0b00111111 11111111
    msg_type_and_length = (type << (2 * 8 - 2)) | msglen

    timestamp = int(time.time())

    code = code if code is not None else len(user)

    # <=little endian (for incompatibility)
    # H=unsigned short (2B) - type (2b) + msg_length (14b)
    # I=unsigned int (4B) - timestamp
    # B=unsigned char (1B) - code (error_code / username_length)
    header = struct.pack("<HIB", msg_type_and_length, timestamp, code)

    return header + encoded_message + user


def format_ts(timestamp):
    ts = datetime.datetime.fromtimestamp(int(timestamp))
    return "{hour:0>2}:{minute:0>2}".format(hour=ts.hour, minute=ts.minute)


def format_message(msg):
    if msg["type"] == TYPE["public"]:
        return "{ts} [{author}] {message}".format(
            ts=format_ts(msg["timestamp"]),
            author=msg["username"],
            message=msg["message"],
        )
    elif msg["type"] == TYPE["private"]:
        return "{ts} ({author}) {message}".format(
            ts=format_ts(msg["timestamp"]),
            author=msg["username"],
            message=msg["message"],
        )
    elif msg["type"] == TYPE["error"]:
        return "{ts} (SERVER) {message}".format(
            ts=format_ts(msg["timestamp"]),
            message=msg["message"],
        )
    else:  # (msg["type"] == TYPE["username"])
        return "unknown message type: " + str(msg["type"])


def strlen(s):
    return len(re.compile(r"\x1b\[[;\d]*[A-Za-z]", re.VERBOSE).sub("", s))
