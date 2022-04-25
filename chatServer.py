import signal

signal.signal(signal.SIGINT, signal.SIG_DFL)
import socket
import struct
import threading

from common import *

usernames = {}

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
				if client_sock in usernames.values():
					client_sock.send(encode_message(message="User already has a name", type=TYPE["error"], code=ERRORS["invalid_username"]))
					continue
				if msg["username"] in usernames.keys():
					client_sock.send(encode_message(message="Username is taken", type=TYPE["error"], code=ERRORS["invalid_username"]))
					continue
				usernames[msg["username"]] = client_sock
				continue
			if msg["type"] == TYPE["error"]:
				continue
			if msg["message"] is None or len(msg["message"]) == 0:
				continue

			my_name = list(usernames.keys())[list(usernames.values()).index(client_sock)]
			msg["username"] = my_name
			msg["code"] = len(my_name)

			message = format_message(msg)
			print("[{ip}:{port}] {message}".format(
				ip=client_addr[0],
				port=client_addr[1],
				message=message,
			))

			recipients = clients
			if msg["type"] == TYPE["private"]:
				recipients = [usernames[msg["username"]]]

			for client in recipients:
				client.send(encode_message(message=msg["message"], type=msg["type"], user=my_name))
	except ConnectionResetError as e:
		print(e)
		print("Deleting client ...")

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
