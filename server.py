import socket
import json
from urllib.parse import parse_qs

HOST = "0.0.0.0"
PORT = 8080

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))
server.listen(5)

print(f"Server running on {HOST}:{PORT}....")

# -------------------------------------------------------
# ROUTING
# -------------------------------------------------------

ROUTES = {}

def add_route(path, handler):
    ROUTES[path] = handler


def home_handler(request):
    return ("<h1>Home</h1>", 200, {"Content-Type": "text/html"})


def about_handler(request):
    return ("<h1>About</h1>", 200, {"Content-Type": "text/html"})


def login_handler(request):
    if request["method"] != "POST":
        return ("<h1>405 Method Not Allowed</h1>", 405, {"Content-Type": "text/html"})

    if request.get("json"):
        username = request["json"].get("username", "unknown")
    else:
        username = request.get("form", {}).get("username", "unknown")

    return (f"<h1>Welcome, {username}</h1>", 200, {"Content-Type": "text/html"})


add_route("/", home_handler)
add_route("/about", about_handler)
add_route("/login", login_handler)

# -------------------------------------------------------
# RESPONSE BUILDER
# -------------------------------------------------------

def build_response(body, status=200, headers=None):
    status_texts = {
        200: "OK",
        404: "Not Found",
        400: "Bad Request",
        500: "Internal Server Error"
    }

    response = (
        f"HTTP/1.1 {status} {status_texts.get(status, 'OK')}\r\n"
        f"Content-Length: {len(body)}\r\n"
    )

    if headers:
        for k, v in headers.items():
            response += f"{k}: {v}\r\n"

    response += "\r\n" + body
    return response

# -------------------------------------------------------
# MAIN LOOP
# -------------------------------------------------------

while True:
    client_socket, client_addr = server.accept()
    print("A Wild client appeared:", client_addr)

    data = client_socket.recv(1024).decode()

    if not data:
        client_socket.close()
        continue

    # ---------------------------
    # REQUEST LINE
    # ---------------------------
    lines = data.split("\r\n")
    method, path, protocol = lines[0].split(" ", 2)

    # ---------------------------
    # QUERY PARAMS
    # ---------------------------
    raw_path, _, query_string = path.partition("?")
    params = {}

    if query_string:
        for part in query_string.split("&"):
            if "=" in part:
                key, value = part.split("=", 1)
                params[key] = value

    # ---------------------------
    # HEADERS
    # ---------------------------
    headers = {}
    for line in lines[1:]:
        if line == "":
            break
        if ":" in line:
            key, value = line.split(":", 1)
            headers[key.strip()] = value.strip()

    # ---------------------------
    # BODY READING (POST ONLY)
    # ---------------------------

    content_length = int(headers.get("Content-Length", 0))

    try:
        empty_line_index = lines.index("")
    except ValueError:
        empty_line_index = len(lines) - 1

    body_data = "\r\n".join(lines[empty_line_index + 1:])
    body = body_data

    remaining = content_length - len(body_data)

    while remaining > 0:
        chunk = client_socket.recv(remaining).decode()
        body += chunk
        remaining -= len(chunk)

    # ---------------------------
    # BODY PARSING
    # ---------------------------

    content_type = headers.get("Content-Type", "").split(";")[0].strip().lower()
    form = {}
    json_data = {}

    if content_type == "application/x-www-form-urlencoded":
        parsed = parse_qs(body, keep_blank_values=True)
        for k, vlist in parsed.items():
            form[k] = vlist[0] if len(vlist) == 1 else vlist

    elif content_type == "application/json":
        try:
            json_data = json.loads(body) if body else {}
        except:
            json_data = {}

    # ---------------------------
    # REQUEST OBJECT
    # ---------------------------

    request = {
        "method": method,
        "path": raw_path,
        "protocol": protocol,
        "headers": headers,
        "params": params,
        "body": body,
        "form": form,
        "json": json_data
    }

    # ---------------------------
    # ROUTER DISPATCH
    # ---------------------------
    handler = ROUTES.get(raw_path)

    if handler:
        body, status, extra_headers = handler(request)
    else:
        body = "<h1>404 Not Found</h1>"
        status = 404
        extra_headers = {"Content-Type": "text/html"}

    # ---------------------------
    # SEND RESPONSE
    # ---------------------------
    response = build_response(body, status, extra_headers)
    client_socket.sendall(response.encode("utf-8"))
    client_socket.close()
