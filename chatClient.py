import math
import socket
import struct
import sys
import threading
import time

import pycat
from common import *
from pycat import colour, windows

if len(sys.argv) > 1:
    server_address = sys.argv[1].split(":")[0]
    server_port = int(sys.argv[1].split(":")[1])
else:
    server_address = "localhost"
    server_port = 1234
SERVER = (server_address, server_port)

username = None
COLOUR_SETTINGS = {
    # status bar
    "status": {"foreground": "green"},
    "username": {"foreground": "yellow"},
    "ip": {"foreground": "yellow"},
    "error": {"foreground": "bright_red"},
    # message area
    "ts": {},
    "log": {"foreground": "bright_blue"},  # log message colour
    # senders
    "server": {"foreground": "bright_red"},
    "foreign_user": {"foreground": "bright_magenta"},
    "local_user": {"foreground": "yellow"},
}


def send_message(sock, message):
    if len(message) >= 1 << 14:
        log("Message too long: " + message)
        return
    encoded = encode_message(message=message, type=TYPE["public"])
    sock.sendall(encoded)


def send_dm(sock, message, recipient):
    if len(message) >= 1 << 14:
        log("Message too long: " + message)
        return
    if len(recipient) >= 1 << 8:
        log("Recipient name too long: " + recipient)
        return
    display_dm(message, username, recipient)
    encoded = encode_message(message=message, type=TYPE["private"], user=recipient)
    if recipient != username:
        sock.sendall(encoded)


def send_name(sock, username):
    if len(username) >= 1 << 8:
        log("Username too long")
        return change_username()
    encoded = encode_message(type=TYPE["username"], user=username)
    sock.sendall(encoded)


###


# message_receiver funkcija tece v loceni niti
def message_receiver():
    global connected_users
    global chat_window
    global participants_window
    global canvas

    while True:
        msg = receive_message(sock)
        if msg["type"] == TYPE["username"]:
            if msg["message"] == "0":
                if msg["username"] in connected_users:
                    connected_users.remove(msg["username"])
                    log(msg["username"] + " disconnected")
            elif msg["message"] == "1":
                connected_users.append(msg["username"])
                if msg["username"] == username:
                    name = colour.Colour(msg["username"], COLOUR_SETTINGS["local_user"])
                else:
                    name = colour.Colour(
                        msg["username"], COLOUR_SETTINGS["foreign_user"]
                    )
                log("User " + name + " connected.")
            else:
                # username is confirmed OK
                set_username(msg["username"])
            participants_window.clear()
            for u in connected_users:
                participants_window.print(u)
            canvas.refresh(participants_window)
        elif msg["type"] == TYPE["error"]:
            handle_error(msg)
        else:
            # regular chat message
            author = msg["username"]
            message = msg["message"]

            if msg["type"] == TYPE["error"]:
                display_error_msg(message)
                continue

            if msg["type"] == TYPE["private"]:
                display_dm(message, from_user=author, to_user=username)
            else:
                display_public_msg(message, author)


def handle_error(msg):
    if msg["code"] == ERRORS["invalid_username"]:
        log(msg["message"])
        change_username()
    if msg["code"] == ERRORS["dm_not_found"]:
        log("Error: " + msg["message"])


def get_input(prompt):
    input_window.clear()
    canvas.refresh()
    pos = input_window.position
    pycat.cursor.move(*input_window.inner_position)
    return input(prompt)


def change_username():
    username = get_input("Enter a username: ")
    input_window.print("Logging in ...")
    send_name(sock, username)


def title_text(left, center, right, available_width):
    width_left = int(math.floor(available_width / 2.0))
    width_right = int(math.ceil(available_width / 2.0))
    padding_left = width_left - strlen(left) - int(math.floor(strlen(center) / 2.0))
    padding_right = width_right - strlen(right) - int(math.ceil(strlen(center) / 2.0))
    return left + padding_left * " " + center + padding_right * " " + right


def set_status(status, redraw=True):
    available_width = status_window.inner_size[0]
    title = "=== Welcome to RKChat ==="
    icons = "_  □  X "
    coloured_status = colour.Colour(status, COLOUR_SETTINGS["status"])
    text = title_text(coloured_status, title, icons, available_width)
    status_window.clear()
    status_window.print(text)
    if redraw:
        canvas.refresh(status_window)
    else:
        canvas.render(status_window)


def display_error_msg(message, redraw=True):
    author = colour.Colour("SERVER", COLOUR_SETTINGS["server"])
    display_message(message, author, redraw)


def display_public_msg(message, from_user, redraw=True):
    col = "local_user" if from_user == username else "foreign_user"
    author = colour.Colour(from_user, COLOUR_SETTINGS[col])
    display_message(message, author, redraw)


def display_dm(message, from_user, to_user, redraw=True):
    from_colour = COLOUR_SETTINGS["foreign_user"]
    to_colour = COLOUR_SETTINGS["foreign_user"]
    if from_user == username:
        from_colour = COLOUR_SETTINGS["local_user"]
    if to_user == username:
        to_colour = COLOUR_SETTINGS["local_user"]
    author = (
        colour.Colour(from_user, from_colour)
        + " -> "
        + colour.Colour(to_user, to_colour)
    )
    display_message(message, author, redraw)


def display_message(message, author, redraw=True):
    timestamp = colour.Colour(str(format_ts(time.time())), COLOUR_SETTINGS["ts"])
    chat_window.print(author + " @ " + timestamp)
    chat_window.print(message)
    chat_window.print(" ")
    if redraw:
        canvas.refresh(chat_window)
    else:
        canvas.render(chat_window)


def log(message, redraw=True):
    coloured_message = colour.Colour(message, COLOUR_SETTINGS["log"])
    coloured_author = colour.Colour("LOG", COLOUR_SETTINGS["server"])
    display_message(coloured_message, author=coloured_author, redraw=redraw)


def set_username(uname):
    global username
    log("Login successful.")
    set_status("Logged in as " + colour.Colour(uname, COLOUR_SETTINGS["username"]))
    username = uname


sidebar_width = 30
connected_users = []

w, h = pycat.cursor.get_terminal_size()
status_window = pycat.Window(position=(0, 0), size=(w, 3))
chat_window = pycat.windows.ConsoleWindow(
    position=(0, 2), size=(w - sidebar_width + 1, h - 4)
)
participants_title = pycat.windows.Window(
    position=(w - sidebar_width, 2), size=(sidebar_width, 3)
)
participants_window = pycat.windows.ListWindow(
    position=(w - sidebar_width, 4), size=(sidebar_width, h - 6)
)
input_window = pycat.windows.InputWindow(position=(0, h - 3), size=(w, 3))
canvas = pycat.Canvas(
    [chat_window, participants_window, participants_title, status_window, input_window]
)
participants_title.print("Online users")

for i in range(canvas.size[1] - 1):
    print(".")  # console padding


if len(sys.argv) > 1 and sys.argv[1] == "help":
    interactive_help()
    sys.exit(0)


set_status(colour.Colour("Connecting ...", COLOUR_SETTINGS["error"]), redraw=False)
log("Connecting to " + colour.Colour(str(SERVER), COLOUR_SETTINGS["ip"]) + " ...")

while True:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(SERVER)
    except Exception as e:
        set_status(str(e))
        log(str(e))
        get_input("Press Enter to attempt to reconnect or Ctrl-C to quit.")
        log("Reconnecting ...")
        set_status("Connecting ...")
        continue
    break
set_status("Connected to " + colour.Colour(str(SERVER), COLOUR_SETTINGS["ip"]))
log("Connected.")

# begin receiving messages
thread = threading.Thread(target=message_receiver)
thread.daemon = True
thread.start()

# select username
change_username()

while username is None:
    time.sleep(0.1)

# await input
while True:
    try:
        time.sleep(0.1)
        msg_send = get_input("> ")
        if msg_send.startswith("@"):
            args = msg_send.split()
            if len(args) >= 2:
                recipient = args[0][1:]
                message = " ".join(args[1:])
                send_dm(sock, message, recipient)
                continue
        send_message(sock, msg_send)
    except KeyboardInterrupt:
        sys.exit(0)
