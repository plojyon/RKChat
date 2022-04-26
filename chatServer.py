import signal

signal.signal(signal.SIGINT, signal.SIG_DFL)
import socket
import struct
import threading

from common import *

sock_to_uname = {}
uname_to_sock = {}

def add_user(socket, username):
	if socket in sock_to_uname:
		socket.send(encode_message(message="User already has a name", type=TYPE["error"], code=ERRORS["invalid_username"]))
		return False
	if username in uname_to_sock:
		socket.send(encode_message(message="Username is taken", type=TYPE["error"], code=ERRORS["invalid_username"]))
		return False

	# confirm username with client
	try:
		socket.send(encode_message(message="2", type=TYPE["username"], user=username))
	except:
		pass

	# broadcast new client to everyone
	for client in clients:
		try:
			client.send(encode_message(message="1", type=TYPE["username"], user=username))
		except:
			pass

	# notify new client of all other logged-in users
	for user in uname_to_sock:
		try:
			client_sock.send(encode_message(message="1", type=TYPE["username"], user=user))
		except:
			pass

	sock_to_uname[socket] = username
	uname_to_sock[username] = socket

	return True

def remove_user(socket):
	username = sock_to_uname[socket]

	# broadcast client loss
	for client in set(clients) - set([socket]):
		try:
			client.send(encode_message(message="0", type=TYPE["username"], user=username))
		except:
			pass

	sock_to_uname.pop(socket, None)
	uname_to_sock.pop(username, None)


# funkcija za komunikacijo z odjemalcem (tece v loceni niti za vsakega odjemalca)
def client_thread(client_sock, client_addr):
	global clients
	global usernames

	print("[system] connected with " + client_addr[0] + ":" + str(client_addr[1]))
	print("[system] we now have " + str(len(clients)) + " clients")

	try:
		while True:
			msg = receive_message(client_sock)
			if msg["type"] == TYPE["username"]:
				add_user(client_sock, msg["username"])
				continue
			if msg["type"] == TYPE["error"]:
				continue
			if msg["message"] is None or len(msg["message"]) == 0:
				continue

			msg["username"] = sock_to_uname[client_sock]
			msg["code"] = len(sock_to_uname[client_sock])

			message = format_message(msg)
			print("[{ip}:{port}] {message}".format(
				ip=client_addr[0],
				port=client_addr[1],
				message=message,
			))

			# determine set of intended recipients
			recipients = clients
			if msg["type"] == TYPE["private"]:
				recipients = [usernames[msg["username"]]]

			# send message to intended recipients
			for client in recipients:
				client.send(encode_message(message=msg["message"], type=msg["type"], user=sock_to_uname[client_sock]))
	except ConnectionResetError as e:
		print(e)
		print("Deleting client ...")
		remove_user(client_sock)

	with clients_lock:
		clients.remove(client_sock)
	print("[system] we now have " + str(len(clients)) + " clients")
	client_sock.close()

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind(("localhost", PORT))
server_socket.listen(1)

print("[system] listening ...")
clients = set()
clients_lock = threading.Lock()
while True:
	try:
		# pocakaj na novo povezavo - blokirajoc klic
		client_sock, client_addr = server_socket.accept()
		with clients_lock:
			clients.add(client_sock)

		thread = threading.Thread(target=client_thread, args=(client_sock, client_addr));
		thread.daemon = True
		thread.start()

	except KeyboardInterrupt:
		break

print("[system] closing server socket ...")
server_socket.close()
