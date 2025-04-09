# Basic peer node implementation
import hashlib 
import socket 
import threading 
import json 

class Peernode:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port 
        self.node_id = self.generate_node_id() 
        self.routing_table = {} #Store known peers 
        self.data_store = {} #DHT key-value pair 
        
    def generate_node_id(self):
        """Genrate a unique id for peer using SHA-256"""
        unique_string = f"{self.ip} : {self.port}"
        return hashlib.sha256(unique_string.encode()).hexdigest()[ :16]
    
    def start_server(self):
        """ Start listening for incoming peer connections"""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind((self.ip, self.port))
        server.listen(5)
        print(f"Peer {self.node_id} listening on {self.ip}:{self.port}")
        
        while True :
            client_socket, address = server.accept()
            threading.Thread(target= self.handle_peer, args = (client_socket,)).start()
            
        def handle_peer(self, client_socket):
            #Handling incoming peer messages 
            try:
                data = client_socket.recv(1024).decode()
                
                if data:
                    request = json.loads(data)
                    request = self.process_request(request)
                    client_socket.send(json.dumps(response).encode())
            except Exception as e:
                print(f"Error handling peer: {e}")
            finally:
                client_socket.close()
        
        def process_request(self, request):
            #Process incoming requests(storing or retrieving file info).
            command = request.get("command")
            
            if command == "ping":
                return {"status" : "alive"}
            
            elif command == 'store':
                key, value =request.get("key"), request.get("value")
                self.data_store[key] = value
                return {"status" : "stored" ,'key' : key}
            
            elif command == "find":
                key = request.get('key')
                return {"value": self.data_store(key, 'notfound')}
            
            return {"error" : 'invalid command'}        