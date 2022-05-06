import socket
import struct
import sys
import threading
import time
import getpass
import math

import pycat
from pycat import windows
from pycat import colour
from common import *

SERVER = ("localhost", PORT)
username = None
COLOUR_SETTINGS = {
    # status bar
    "status": {"foreground": "green"},
    "username": {"foreground": "yellow"},
    "ip": {"foreground": "yellow"},
    "error": {"foreground": "bright_red"},

    # message area
    "ts": {},
    "log": {"foreground": "bright_blue"}, # log message colourF
    # senders
    "server": {"foreground": "bright_red"},
    "unknown_user": {"foreground": "bright_magenta"},
    "known_user": {"foreground": "yellow"},
}

def interactive_help():
    participants_window.print("fake_user_1")
    participants_window.print("fake_user_2")
    participants_window.print("fake_user_3")
    participants_window.print("fake_user_4_with_a_long_nickname")

    #display_message(message, colour_setting="server", author="LOG", parentheses="[]", redraw=True):
    log("Welcome to RKChat!", redraw=False)
    set_status("This is a "+colour.Yellow("status bar"), redraw=False)

    msg = "This is the message area. Messages from other users will appear here."
    display_message(msg, colour_setting="unknown_user", author="Yon", parentheses="[]", redraw=False)

    msg = "The message author is enclosed in [square brackets]."
    display_message(msg, colour_setting="unknown_user", author="Yon", parentheses="[]", redraw=False)

    msg = "If the message is directed only at you, it's enclosed in (parentheses)."
    display_message(msg, colour_setting="unknown_user", author="Yon", parentheses="()", redraw=False)

    log("System messages and logs look like this.", redraw=False)

    msg = "Try sending a public message now. Type something in the input box and press enter."
    display_message(msg, colour_setting="unknown_user", author="Yon", parentheses="[]", redraw=False)

    reply = get_input("Type a message here: ")
    display_message(reply, colour_setting="known_user", author="user", parentheses="[]", redraw=False)

    msg = "Nice! Notice your username displays in yellow, in case you forget who you are."
    display_message(msg, colour_setting="unknown_user", author="Yon", parentheses="[]", redraw=False)

    msg = "Try sending me a private message now. Prefix your message with @Yon."
    display_message(msg, colour_setting="unknown_user", author="Yon", parentheses="[]", redraw=False)

    while not (reply.startswith("@Yon ") and len(reply) > len("@Yon ")):
        reply = get_input("Send a private message to Yon: ")
        if not (reply.startswith("@Yon ") and len(reply) > len("@Yon ")):
            msg = "Not good. You must your message with @Yon. Like this: \"@Yon hello, Yon!\""
            display_message(msg, colour_setting="unknown_user", author="Yon", parentheses="[]", redraw=False)
    reply = reply[len("@Yon "):]
    display_message(reply, colour_setting="known_user", author="user", parentheses="()", redraw=False)

    msg = "Good job! You're ready to chat now. Hit Ctrl-C to exit and restart this script without the help."
    display_message(msg, colour_setting="unknown_user", author="Yon", parentheses="[]", redraw=False)

    canvas.refresh()

    try:
        while True:
            time.sleep(1)
    except:
        sys.exit(0)

def send_message(sock, message):
    if len(message) >= 1 << 14:
        raise ValueError("Message too long")
    encoded = encode_message(message=message, type=TYPE["public"])
    sock.sendall(encoded)


def send_dm(sock, message, recipient):
    if len(message) >= 1 << 14:
        raise ValueError("Message too long")
    if len(recipient) >= 1 << 8:
        raise ValueError("Recipient name too long")
    encoded = encode_message(message=message, type=TYPE["private"], user=recipient)
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
                    name = colour.Colour(msg["username"], COLOUR_SETTINGS["known_user"])
                else:
                    name = colour.Colour(msg["username"], COLOUR_SETTINGS["unknown_user"])
                log(name + " connected")
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
            author=msg["username"]
            message=msg["message"]
            parentheses = "[]"

            if msg["type"] == TYPE["error"]:
                author = "SERVER"
                colour_setting = "server"
                parentheses = "()"
            elif author == username:
                colour_setting = "known_user"
            else:
                colour_setting = "unknown_user"

            if msg["type"] == TYPE["private"]:
                parentheses = "()"
            display_message(message, colour_setting, author, parentheses)


def handle_error(msg):
    if msg["code"] == ERRORS["invalid_username"]:
        log(msg["message"])
        change_username()
    if msg["code"] == ERRORS["banned"]:
        sys.exit(0)


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


def display_message(message, colour_setting="server", author="LOG", parentheses="[]", redraw=True):
    timestamp = colour.Colour(str(format_ts(time.time())), COLOUR_SETTINGS["ts"])
    sender = parentheses[0] + author + parentheses[1]
    coloured_sender = colour.Colour(sender, COLOUR_SETTINGS[colour_setting])
    chat_window.print(timestamp + " " + coloured_sender + " " + message)
    if redraw:
        canvas.refresh(chat_window)
    else:
        canvas.render(chat_window)


def log(message, redraw=True):
    coloured_message = colour.Colour(message, COLOUR_SETTINGS["log"])
    display_message(coloured_message, author="LOG", parentheses="()", redraw=redraw)


def set_username(uname):
    global username
    log(colour.Green("Login successful."))
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
    position=(w - sidebar_width, 2), size=(sidebar_width, 3))
participants_window = pycat.windows.ListWindow(
    position=(w - sidebar_width, 4), size=(sidebar_width, h - 6)
)
input_window = pycat.windows.InputWindow(position=(0, h - 3), size=(w, 3))
canvas = pycat.Canvas([chat_window, participants_window, participants_title, status_window, input_window])

participants_title.print("Online users")


if len(sys.argv) > 1 and sys.argv[1] == "help":
    interactive_help()
    sys.exit(0)


set_status(colour.Colour("Connecting ...", COLOUR_SETTINGS["error"]), redraw=False)
log("Connecting to " + colour.Colour(str(SERVER), COLOUR_SETTINGS["ip"]))

while True:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(SERVER)
    except Exception as e:
        set_status()
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
        if msg_send.startswith("/dm "):
            args = msg_send.split()
            if len(args) >= 3:
                recipient = args[1]
                message = " ".join(args[2:])
                send_dm(sock, message, recipient)
                continue
        send_message(sock, msg_send)
    except KeyboardInterrupt:
        sys.exit(0)
