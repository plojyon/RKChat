import socket
import struct
import sys
import threading
import time
import getpass

from common import *


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
		raise ValueError("Username too long")
	encoded = encode_message(type=TYPE["username"], user=username)
	sock.sendall(encoded)

###

# message_receiver funkcija tece v loceni niti
def message_receiver():
	while True:
		msg = receive_message(sock)
		print(format_message(msg))

def handle_error(msg):
	if (msg["code"] == ERRORS["invalid_username"]):
		change_username()
	if (msg["code"] == ERRORS["banned"]):
		sys.exit(0)

def change_username():
	username = input("Enter a username: ")
	send_name(sock, username)

# connect to the server
print("[LOCAL] connecting to chat server ...")
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(("localhost", PORT))
print("[LOCAL] connected!")

# begin receiving messages
thread = threading.Thread(target=message_receiver)
thread.daemon = True
thread.start()

# select username
change_username()

# await input
while True:
	try:
		time.sleep(0.1)
		msg_send = input("> ")
		print("\b\r\b\r", end="")
		send_message(sock, msg_send)
	except KeyboardInterrupt:
		sys.exit(0)
