import signal
import socket
import struct
import sys
import threading

from common import *

signal.signal(signal.SIGINT, signal.SIG_DFL)

sock_to_uname = {}
uname_to_sock = {}

lowercase = [chr(i) for i in range(ord("a"), ord("z") + 1)]
uppercase = [i.upper() for i in lowercase]
digits = [str(i) for i in range(10)]
special = ["_", "-"]
legal_characters = lowercase + uppercase + digits + special


def validate_username(username):
    for ch in username:
        if ch not in legal_characters:
            return False
    return True


def add_user(socket, username):
    if socket in sock_to_uname:
        socket.send(
            encode_message(
                message="User already has a name",
                type=TYPE["error"],
                code=ERRORS["invalid_username"],
            )
        )
        return False
    if username in uname_to_sock:
        socket.send(
            encode_message(
                message="Username is taken",
                type=TYPE["error"],
                code=ERRORS["invalid_username"],
            )
        )
        return False
    if not validate_username(username):
        socket.send(
            encode_message(
                message="Username contains illegal characters. Allowed characters: "
                + str(legal_characters),
                type=TYPE["error"],
                code=ERRORS["invalid_username"],
            )
        )
        return False

    # confirm username with client
    try:
        socket.send(encode_message(message="2", type=TYPE["username"], user=username))
    except:
        pass

    # broadcast new client to everyone
    for client in clients:
        try:
            client.send(
                encode_message(message="1", type=TYPE["username"], user=username)
            )
        except:
            pass

    # notify new client of all other logged-in users
    for user in uname_to_sock:
        try:
            client_sock.send(
                encode_message(message="1", type=TYPE["username"], user=user)
            )
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
            client.send(
                encode_message(message="0", type=TYPE["username"], user=username)
            )
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

            # determine set of intended recipients
            recipients = clients
            if msg["type"] == TYPE["private"]:
                if msg["username"] in uname_to_sock:
                    recipients = [uname_to_sock[msg["username"]]]
                else:
                    client.send(
                        encode_message(
                            message="Trying to DM a nonexistent user",
                            type=TYPE["error"],
                            code=ERRORS["dm_not_found"],
                        )
                    )

            # format message for logging
            msg["username"] = sock_to_uname[client_sock]
            msg["code"] = len(sock_to_uname[client_sock])
            message = str(msg)
            print(
                "[{ip}:{port}] {message}".format(
                    ip=client_addr[0],
                    port=client_addr[1],
                    message=message,
                )
            )

            # send message to intended recipients
            for client in recipients:
                try:
                    client.send(
                        encode_message(
                            message=msg["message"],
                            type=msg["type"],
                            user=sock_to_uname[client_sock],
                        )
                    )
                except BrokenPipeError:
                    pass
    except ConnectionResetError as e:
        print(e)
        print("Deleting client ...")
        remove_user(client_sock)
    except RuntimeError as e:
        print(e)  # socket connection broken
        print("Deleting client ...")
        remove_user(client_sock)

    with clients_lock:
        clients.remove(client_sock)
    print("[system] we now have " + str(len(clients)) + " clients")
    client_sock.close()


if len(sys.argv) > 1:
    server_address = sys.argv[1].split(":")[0]
    server_port = int(sys.argv[1].split(":")[1])
else:
    server_address = "localhost"
    server_port = 1234

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind((server_address, server_port))
server_socket.listen(1)

print("[system] listening @ " + str((server_address, server_port)))
clients = set()
clients_lock = threading.Lock()
while True:
    try:
        # pocakaj na novo povezavo - blokirajoc klic
        client_sock, client_addr = server_socket.accept()
        with clients_lock:
            clients.add(client_sock)

        thread = threading.Thread(target=client_thread, args=(client_sock, client_addr))
        thread.daemon = True
        thread.start()

    except KeyboardInterrupt:
        break

print("[system] closing server socket ...")
server_socket.close()
