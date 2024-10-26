import socket
import threading
import logging
import select

# Set up logging configuration
logging.basicConfig(filename='proxy_log.txt', level=logging.INFO, format='%(asctime)s - %(message)s')

# Function to forward data between client and remote server
def forward_data(source, destination):
    try:
        data = source.recv(4096)
        if len(data) > 0:
            destination.send(data)
        return len(data)
    except Exception as e:
        logging.error(f"Error forwarding data: {str(e)}")
        return 0

# This function will handle the client requests
def handle_client(client_socket):
    try:
        request = client_socket.recv(1024).decode('utf-8')

        # Log the client request details
        logging.info(f"Client Request: {request}")

        # Display the client's request
        print(f"[CLIENT REQUEST]: {request}")

        # Check if the request is for HTTPS (CONNECT method)
        if "CONNECT" in request:
            # Extract the host and port for HTTPS connection
            host_port = request.split(" ")[1]
            remote_host, remote_port = host_port.split(":")
            
            # Acknowledge the HTTPS connection to the client
            client_socket.send(b"HTTP/1.1 200 Connection established\r\n\r\n")
            
            # Create a tunnel between client and remote server
            remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            remote_socket.connect((remote_host, int(remote_port)))

            # Forward data between the client and the remote server using a loop
            sockets = [client_socket, remote_socket]
            while True:
                read_sockets, _, error_sockets = select.select(sockets, [], sockets, 5)
                if error_sockets:
                    break
                for sock in read_sockets:
                    if sock == client_socket:
                        if forward_data(client_socket, remote_socket) == 0:
                            break
                    elif sock == remote_socket:
                        if forward_data(remote_socket, client_socket) == 0:
                            break
            remote_socket.close()

        else:
            # Handle normal HTTP requests
            first_line = request.split('\n')[0]
            url = first_line.split(' ')[1]
            if url.startswith("http://"):
                url = url[7:]  # Remove "http://"
            host = url.split('/')[0]  # Extract the host

            # Connect to the target host
            remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            remote_socket.connect((host, 80))

            # Send the client's HTTP request to the remote server
            remote_socket.send(request.encode('utf-8'))

            # Receive the response from the remote server and send it back to the client
            while True:
                response = remote_socket.recv(4096)
                if len(response) > 0:
                    client_socket.send(response)
                else:
                    break

            remote_socket.close()

    except Exception as e:
        logging.error(f"Error handling request: {str(e)}")

    client_socket.close()

def start_proxy_server(server_ip, server_port):
    # Create a server socket
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((server_ip, server_port))
    server.listen(5)

    print(f"[*] Proxy server listening on {server_ip}:{server_port}")

    while True:
        # Accept incoming connections
        client_socket, addr = server.accept()

        # Display the connection information
        print(f"[CONNECTION] Accepted connection from {addr}")

        # Handle the client's request in a new thread
        client_handler = threading.Thread(target=handle_client, args=(client_socket,))
        client_handler.start()

if __name__ == "__main__":
    # Start the proxy server
    start_proxy_server("127.0.0.1", 8080)

