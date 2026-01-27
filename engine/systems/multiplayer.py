__all__ = ["MultiplayerManager"]

import socket
import json
import threading
import time
from engine.world.constants import MultiplayerAction

class MultiplayerManager:
    def __init__(self, mode="off", transport="wifi", host="127.0.0.1", port=5000, tick_rate=20):
        self.mode = mode  # "off", "server", "client"
        self.transport = transport
        self.host = host
        self.port = port
        self.tick_rate = tick_rate

        self.sock = None
        self.clients = []  # solo se server
        self.running = False
        self.last_state = {}  # ultima copia di stato inviato
        self.state_callback = None  # funzione per integrare col World

    # ==============================
    # Avvio
    # ==============================
    def start(self):
        if self.mode == "server":
            print("[multiplayer] starting server...")
            self._start_server()
        elif self.mode == "client":
            print("[multiplayer] starting client...")
            self._start_client()

    # ==============================
    # Server side
    # ==============================
    def _start_server(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))
        self.sock.listen(5)
        self.running = True
        threading.Thread(target=self._accept_clients, daemon=True).start()
        threading.Thread(target=self._server_loop, daemon=True).start()

    def _accept_clients(self):
        while self.running:
            client, addr = self.sock.accept() # type: ignore
            self.clients.append(client)
            threading.Thread(target=self._handle_client, args=(client,), daemon=True).start()

    def _handle_client(self, client):
        while self.running:
            try:
                data = client.recv(4096)
                if not data: break
                msg = json.loads(data.decode())

                if msg["type"] == "input":
                    if self.state_callback:
                        self.state_callback(MultiplayerAction.INPUT, msg)  # server elabora input
                        print(f"[multiplayer] Server > updating world with: {msg}")
                elif msg["type"] == "ack":
                    print(f"[multiplayer] ack from {client.getpeername()} = {msg['ack']}")
            except:
                break
        client.close()

    def _server_loop(self):
        interval = 1.0 / self.tick_rate
        last_sent = time.time()
        ack_counter = 0

        while self.running:
            time.sleep(interval)
            sent = False

            if self.state_callback:
                # Ottieni stato aggiornato dal World
                state = self.state_callback(MultiplayerAction.GET_STATE, None)

                # Delta update
                delta = {k: v for k,v in state.items() if self.last_state.get(k) != v} # type: ignore
                if delta:
                    packet = {"type": "state_update", "tick": time.time(), **delta}
                    self.broadcast(packet)
                    self.last_state = state.copy()
                    last_sent = time.time()
                    sent = True

                # Se troppo tempo senza invio → manda ack
            if not sent and (time.time() - last_sent > 1.0):  # 2s senza pacchetti
                ack_counter += 1
                packet = {"type": "ack", "ack": ack_counter}
                self.broadcast(packet)
                last_sent = time.time()
                print(f"[multiplayer] sleep time over, sending ack: {packet}")

    # ==============================
    # Client side
    # ==============================
    def _start_client(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))
        self.running = True
        threading.Thread(target=self._listen_server, daemon=True).start()

    def _listen_server(self):
        while self.running:
            try:
                data = self.sock.recv(4096) # type: ignore
                if not data: break
                msg = json.loads(data.decode())

                if msg["type"] == "ack":
                    # Rispondi con ack+1
                    reply = {"type": "ack", "ack": msg["ack"] + 1}
                    self.sock.sendall(json.dumps(reply).encode()) # type: ignore
                    print(f"[multiplayer] Client > updating self.world with: {msg}")
                    continue

                if self.state_callback:
                    self.state_callback(MultiplayerAction.UPDATE_STATE, msg)  # client aggiorna il World
                    print(f"[multiplayer] Client > updating self.world with: {msg}")
            except:
                break

    # ==============================
    # API pubbliche
    # ==============================
    def send_input(self, data):
        """Client manda input al server"""
        if self.mode == "client" and self.running:
            msg = json.dumps({"type": "input", **data}).encode()
            self.sock.sendall(msg) # type: ignore

    def broadcast(self, data):
        """Server manda stato a tutti i client"""
        msg = json.dumps(data).encode()
        for c in self.clients:
            try: c.sendall(msg)
            except: pass

    def stop(self):
        self.running = False
        if self.sock: self.sock.close()
