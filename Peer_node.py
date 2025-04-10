import hashlib
import socket
import threading
import json

class PeerNode:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.node_id = self.generate_node_id()
        self.routing_table = {}  # Stores known peers
        self.data_store = {}  # DHT key-value store (file_hash -> peer list)

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
        """Process incoming requests for storing or retrieving file information."""
        command = request.get("command")

        if command == "ping":
            return {"status": "alive"}

        elif command == "store":
            key, value = request.get("key"), request.get("value")
            if key in self.data_store:
                self.data_store[key].append(value)  # Append new peer
            else:
                self.data_store[key] = [value]  # Create new entry
            return {"status": "stored", "key": key}

        elif command == "find":
            key = request.get("key")
            if key in self.data_store:
                return {"peers": self.data_store[key]}  # Return list of peers with file
            else:
                return self.forward_request(key)  # Forward lookup

        return {"error": "invalid command"}

    def forward_request(self, key):
        """Forward file search request to known peers if not found locally."""
        for peer_address in self.routing_table:
            try:
                peer_ip, peer_port = peer_address.split(":")
                peer_port = int(peer_port)

                client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client.connect((peer_ip, peer_port))
                client.send(json.dumps({"command": "find", "key": key}).encode())

                response = json.loads(client.recv(1024).decode())
                client.close()

                if "peers" in response and response["peers"] != "not found":
                    return response  # Found file in another peer

            except Exception as e:
                print(f"Failed to contact peer {peer_address}: {e}")

        return {"peers": "not found"}  # If no peers have the file

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

    def store_file(self, filename):
        """Store file hash in the DHT."""
        file_hash = hashlib.sha256(filename.encode()).hexdigest()
        self.data_store[file_hash] = [f"{self.ip}:{self.port}"]
        print(f"Stored {filename} with hash {file_hash}")

    def find_file(self, filename):
        """Find peers that have the requested file."""
        file_hash = hashlib.sha256(filename.encode()).hexdigest()
        print(f"Searching for file {filename} with hash {file_hash}")

        if file_hash in self.data_store:
            return self.data_store[file_hash]  # Return local result
        else:
            return self.forward_request(file_hash)  # Search the network

# Example usage
if __name__ == "__main__":
    peer = PeerNode("127.0.0.1", 5000)
    threading.Thread(target=peer.start_server).start()

    # Manually connect to another peer
    peer.connect_to_peer("127.0.0.1", 5001)

    # Store a file
    peer.store_file("example.txt")

    # Try finding the file
    print(peer.find_file("example.txt"))
