import hashlib
import socket
import threading
import json
import argparse

class PeerNode:
    def __init__(self, ip='127.0.0.1', port=5000, known_peers=None):
        self.ip = ip
        self.port = port
        self.node_id = self.generate_node_id()
        self.routing_table = {}  # Stores known peers (key: 'ip:port')
        self.data_store = {}  # DHT key-value store (file_hash -> peer list)
        
        # Known peers (you can add more manually or load from a config)
        self.known_peers = known_peers if known_peers else []

    def generate_node_id(self):
        """Generate a unique ID for the peer using SHA-256."""
        unique_string = f"{self.ip}:{self.port}"
        return hashlib.sha256(unique_string.encode()).hexdigest()[:16]

    def start_server(self):
        """Start listening for incoming peer connections."""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Allow reuse of the port
        server.bind((self.ip, self.port))
        server.listen(5)
        print(f"[INFO] Peer {self.node_id} is now listening on {self.ip}:{self.port}")

        while True:
            try:
                client_socket, address = server.accept()
                print(f"[INFO] Connection established with {address}")
                threading.Thread(target=self.handle_peer, args=(client_socket,)).start()
            except Exception as e:
                print(f"[ERROR] Failed to accept connection: {e}")

    def handle_peer(self, client_socket):
        """Handle incoming peer messages."""
        try:
            data = client_socket.recv(1024).decode()
            if data:
                request = json.loads(data)
                print(f"[INFO] Received request: {request}")
                response = self.process_request(request)
                client_socket.send(json.dumps(response).encode())
                print(f"[SUCCESS] Sent response: {response}")
        except Exception as e:
            print(f"[ERROR] Error handling peer: {e}")
        finally:
            client_socket.close()
            print("[INFO] Connection closed")

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
                    print(f"[INFO] File found at peer {peer_address}")
                    return response  # Found file in another peer

            except Exception as e:
                print(f"[ERROR] Failed to contact peer {peer_address}: {e}")

        print(f"[INFO] File not found in any connected peers.")
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
                print(f"[SUCCESS] Connected to peer {peer_ip}:{peer_port}")

            client.close()
        except Exception as e:
            print(f"[ERROR] Failed to connect to peer {peer_ip}:{peer_port}: {e}")

    def store_file(self, filename):
        """Store file hash in the DHT."""
        try:
            file_hash = hashlib.sha256(filename.encode()).hexdigest()
            self.data_store[file_hash] = [f"{self.ip}:{self.port}"]
            print(f"[SUCCESS] Stored file '{filename}' with hash {file_hash}")
        except Exception as e:
            print(f"[ERROR] Failed to store file '{filename}': {e}")
            
    def find_file(self, filename):
        """Find peers that have the requested file."""
        try:
            file_hash = hashlib.sha256(filename.encode()).hexdigest()
            print(f"[INFO] Searching for file '{filename}' with hash {file_hash}")

            if file_hash in self.data_store:
                print(f"[SUCCESS] File found locally. Peers: {self.data_store[file_hash]}")
                return self.data_store[file_hash]  # Return local result
            else:
                response = self.forward_request(file_hash)
                if response["peers"] == "not found":
                    print(f"[INFO] File not found in the network.")
                else:
                    print(f"[SUCCESS] File found in the network. Peers: {response['peers']}")
                return response
        except Exception as e:
            print(f"[ERROR] Failed to find file '{filename}': {e}")


    def start(self):
        """Main loop to accept user commands."""
        # Start server in a background thread
        threading.Thread(target=self.start_server, daemon=True).start()

        # Automatically connect to known peers on startup
        for peer_ip, peer_port in self.known_peers:
            self.connect_to_peer(peer_ip, peer_port)

        while True:
            cmd = input("Enter command (store/search/connect/exit): ").strip()
            if cmd == "store":
                filename = input("Filename: ").strip()
                self.store_file(filename)
            elif cmd == "search":
                filename = input("Filename: ").strip()
                self.find_file(filename)
            elif cmd == "connect":
                ip = input("Peer IP: ").strip()
                port = int(input("Peer Port: ").strip())
                self.connect_to_peer(ip, port)
            elif cmd == "exit":
                print("[INFO] Exiting...")
                break
            else:
                print("[ERROR] Unknown command. Please try again.")

# Example usage
if __name__ == "__main__": 
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, required=True, help='Port to run the peer on')
    args = parser.parse_args()

    # You can specify known peers here. For example, [(IP, port)].
    # Default is to have no known peers, but you can set this to known peers.
    known_peers = [("127.0.0.1", 5001)]  # Add other peers to connect to automatically

    peer = PeerNode(port=args.port, known_peers=known_peers)
    peer.start()