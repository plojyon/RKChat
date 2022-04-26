import socket
import struct
import sys
import threading
import time
import getpass
import math

import pycat
from pycat import windows
from common import *

SERVER = ("localhost", PORT)
username = None

### MESSAGE TYPES

def send_message(sock, message):
	if len(message) >= 1<<14:
		raise ValueError("Message too long")
	encoded = encode_message(message=message, type=TYPE["public"])
	sock.sendall(encoded)

def send_dm(sock, message, recipient):
	if len(message) >= 1<<14:
		raise ValueError("Message too long")
	if len(recipient) >= 1<<8:
		raise ValueError("Recipient name too long")
	encoded = encode_message(message=message, type=TYPE["private"], user=recipient)
	sock.sendall(encoded)

def send_name(sock, username):
	if len(username) >= 1<<8:
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
					log(msg["username"]+" disconnected")
			elif msg["message"] == "1":
				connected_users.append(msg["username"])
				log(msg["username"]+" connected")
			else:
				# username is confirmed OK
				set_username(msg["username"])
			participants_window.clear()
			for u in connected_users:
				participants_window.print(u)
			canvas.draw()
		elif msg["type"] == TYPE["error"]:
			handle_error(msg)
		else:
			chat_window.print(format_message(msg))
		canvas.draw()

def handle_error(msg):
	if (msg["code"] == ERRORS["invalid_username"]):
		log(msg["message"])
		change_username()
	if (msg["code"] == ERRORS["banned"]):
		sys.exit(0)

def get_input(prompt):
	input_window.clear()
	canvas.draw()
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
	padding_left = width_left - len(left) - int(math.floor(len(center)/2.0))
	padding_right = width_right - len(right) - int(math.ceil(len(center)/2.0))
	return left + padding_left*" " + center + padding_right*" " + right

def set_status(status):
	available_width = status_window.size[0]-2
	text = title_text(" " + status, "=== Welcome to RKChat ===", "_  □  X ", available_width)
	status_window.clear()
	status_window.print(text)
	canvas.draw()

def set_username(uname):
	global username
	log("Login successful.")
	set_status("Logged in as "+uname)
	username = uname

def log(message):
	chat_window.print(f"{format_ts(time.time())} [LOG] {message}")
	canvas.draw()

sidebar_width = 30
connected_users = []

w,h = pycat.cursor.get_terminal_size()
status_window = pycat.Window(position=(0, 0), size=(w, 3))
chat_window = pycat.windows.ConsoleWindow(position=(0, 2), size=(w-sidebar_width+1,h-4), padding=[1, 2, 1, 2])
participants_window = pycat.windows.ListWindow(position=(w-30, 2), size=(sidebar_width,h), padding=[1, 2, 1, 2])
input_window = pycat.windows.InputWindow(position=(0, h-3), size=(w, 3), padding=[1,1,1,2])
canvas = pycat.Canvas([chat_window, participants_window, status_window, input_window])

canvas.draw()

set_status("Connecting ...")
log("Connecting to "+str(SERVER))

while True:
	try:
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		sock.connect(SERVER)
	except Exception as e:
		set_status("Connection error")
		log(str(e))
		get_input("Press Enter to attempt to reconnect or Ctrl-C to quit.")
		log("Reconnecting ...")
		set_status("Connecting ...")
		continue
	break;
set_status("Connected to "+str(SERVER))
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
		send_message(sock, msg_send)
	except KeyboardInterrupt:
		sys.exit(0)
