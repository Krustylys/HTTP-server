import socket

HOST = "0.0.0.0"
PORT = 8080

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))
server.listen(5)

print(f"Server running on {HOST}:{PORT}....")

# Routing
ROUTES = {}

def add_route(path, handler):
    ROUTES[path] = handler

def home_handler(request):
    return ("<h1>Home</h1>", 200, {"Content-Type":"text/html"})

def about_handler(request):
    return ("<h1>About</h1>", 200, {"Content-Type":"text/html"})

add_route("/", home_handler)
add_route("/about", about_handler)

# Response builder 
def build_response(body, status=200, headers=None):
    status_texts = {
        200: "OK",
        404: "Not Found",
        400: "Bad Request",
        500: "Internal Server Error"
    }

    response = f"HTTP/1.1 {status} {status_texts.get(status, 'OK')}\r\n"
    response += f"Content-Length: {len(body)}\r\n"

    if headers:
        for k, v in headers.items():
            response += f"{k}: {v}\r\n"

    response += "\r\n"
    response += body
    return response

while True:
    client_socket, client_addr = server.accept()
    print("A Wild client appeared:", client_addr)

    data = client_socket.recv(1024).decode()

    if not data:
        client_socket.close()
        continue

    # Request parsing
    lines = data.split("\r\n")
    method, path, protocol = lines[0].split(" ", 2)

    raw_path, _, query_string = path.partition("?")
    params = {}
    if query_string:
        for part in query_string.split("&"):
            if "=" in part:
                key, value = part.split("=", 1)
                params[key] = value

    headers = {}
    for line in lines[1:]:
        if line == "":
            break
        if ":" in line:
            key, value = line.split(":", 1)
            headers[key.strip()] = value.strip()

    request = {
        "method": method,
        "path": raw_path,
        "protocol": protocol,
        "headers": headers,
        "params": params
    }

    # Router
    handler = ROUTES.get(raw_path)

    if handler:
        body, status, extra_headers = handler(request)
    else:
        body = "<h1>404 Not Found</h1>"
        status = 404
        extra_headers = {"Content-Type":"text/html"}

    response = build_response(body, status, extra_headers)
    client_socket.sendall(response.encode("utf-8"))
    client_socket.close()
