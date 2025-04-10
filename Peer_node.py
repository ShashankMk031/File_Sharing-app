import hashlib
import socket
import threading
import json

class PeerNode:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.node_id = self.generate_node_id()
        self.routing_table = {}  # Store known peers
        self.data_store = {}  # DHT key-value store

    def generate_node_id(self):
        """Generate a unique ID for the peer using SHA-256."""
        unique_string = f"{self.ip}:{self.port}"
        return hashlib.sha256(unique_string.encode()).hexdigest()[:16]

    def start_server(self):
        """Start listening for incoming peer connections."""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind((self.ip, self.port))
        server.listen(5)
        print(f"Peer {self.node_id} listening on {self.ip}:{self.port}")

        while True:
            client_socket, address = server.accept()
            threading.Thread(target=self.handle_peer, args=(client_socket,)).start()

    def handle_peer(self, client_socket):
        """Handle incoming peer messages."""
        try:
            data = client_socket.recv(1024).decode()
            if data:
                request = json.loads(data)
                response = self.process_request(request)
                client_socket.send(json.dumps(response).encode())
        except Exception as e:
            print(f"Error handling peer: {e}")
        finally:
            client_socket.close()

    def process_request(self, request):
        """Process incoming requests (for storing or retrieving file info)."""
        command = request.get("command")

        if command == "ping":
            return {"status": "alive"}

        elif command == "store":
            key, value = request.get("key"), request.get("value")
            self.data_store[key] = value
            return {"status": "stored", "key": key}

        elif command == "find":
            key = request.get("key")
            return {"value": self.data_store.get(key, "not found")}

        return {"error": "invalid command"}

    def connect_to_peer(self, peer_ip, peer_port):
        """Connect to another peer and exchange information."""
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect((peer_ip, peer_port))
            client.send(json.dumps({"command": "ping"}).encode())

            response = json.loads(client.recv(1024).decode())
            if response.get("status") == "alive":
                self.routing_table[f"{peer_ip}:{peer_port}"] = True
                print(f"Connected to peer {peer_ip}:{peer_port}")

            client.close()
        except Exception as e:
            print(f"Failed to connect to peer {peer_ip}:{peer_port}: {e}")

# Example usage
if __name__ == "__main__":
    peer = PeerNode("127.0.0.1", 5000)
    threading.Thread(target=peer.start_server).start()

    # Manually connect to another peer
    peer.connect_to_peer("127.0.0.1", 5001)