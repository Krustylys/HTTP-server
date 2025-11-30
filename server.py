import socket
import json
from urllib.parse import parse_qs
import os
import mimetypes
import time


HOST = "0.0.0.0"
PORT = 8080
STATIC_DIR = "static"

def http_date(timestamp):
    return time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(timestamp))

def make_etag(stat):
    return f'"{stat.st_ino}-{stat.st_size}-{int(stat.st_mtime)}"'


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
        301:"Moved Permanently",
        302:"Found",
        304:"Not Modified",
        400:"Bad Request",
        403:"Forbidden",
        404: "Not Found",
        400: "Bad Request",
        500: "Internal Server Error"
    }

    if isinstance(body,bytes):
        body_bytes = body
    else:
        body = "" if body is None else str(body)
        body_bytes = body.encode("utf-8")
    
    
    header = f"HTTP/1.1 {status} {status_texts.get(status, 'OK')}\r\n"
    header += f"Content-Length: {len(body_bytes)}\r\n"
    

    if headers:
        for k, v in headers.items():
            header += f"{k}: {v}\r\n"

    header += "\r\n"
    return header.encode("utf-8") + body_bytes


#static serving
def serve_static(request):
    raw_path = request["path"]
    prefix = "/static/"

    # Not a static request
    if not raw_path.startswith(prefix):
        return None

    rel_path = raw_path[len(prefix):]

    # Null byte check
    if "\x00" in rel_path:
        resp = build_response("<h1>400 Bad Request</h1>", 400, {"Content-Type": "text/html"})
        return resp, None

    # Resolve paths
    requested_fs_path = os.path.realpath(os.path.join(STATIC_DIR, rel_path))
    static_dir_real = os.path.realpath(STATIC_DIR)

    # Directory traversal protection
    try:
        if os.path.commonpath([static_dir_real, requested_fs_path]) != static_dir_real:
            resp = build_response("<h1>403 Forbidden</h1>", 403, {"Content-Type": "text/html"})
            return resp, None
    except Exception:
        resp = build_response("<h1>403 Forbidden</h1>", 403, {"Content-Type": "text/html"})
        return resp, None

    # Directory -> index.html
    if os.path.isdir(requested_fs_path):
        index_path = os.path.join(requested_fs_path, "index.html")
        if os.path.exists(index_path):
            requested_fs_path = index_path
        else:
            resp = build_response("<h1>403 Forbidden</h1>", 403, {"Content-Type": "text/html"})
            return resp, None

    # File exists?
    if not os.path.exists(requested_fs_path):
        resp = build_response("<h1>404 File Not Found</h1>", 404, {"Content-Type": "text/html"})
        return resp, None

    # MIME
    mime_type, _ = mimetypes.guess_type(requested_fs_path)
    if not mime_type:
        mime_type = "application/octet-stream"

    # Stat, ETag, Last-Modified
    try:
        stat = os.stat(requested_fs_path)
    except Exception:
        resp = build_response("<h1>500 Server Error</h1>", 500, {"Content-Type": "text/html"})
        return resp, None

    etag = make_etag(stat)
    last_mod = http_date(stat.st_mtime)

    # Conditional GET (If-None-Match)
    inm = request["headers"].get("If-None-Match")
    if inm and inm.strip() == etag:
        headers = {
            "ETag": etag,
            "Last-Modified": last_mod,
            "Cache-Control": "public, max-age=86400",
            "X-Content-Type-Options": "nosniff"
        }
        resp = build_response("", 304, headers)  # header-only
        return resp, None

    # Build headers for 200 response (no body here)
    headers = {
        "Content-Type": mime_type,
        "X-Content-Type-Options": "nosniff",
        "ETag": etag,
        "Last-Modified": last_mod,
        "Cache-Control": "public, max-age=86400",
        "Content-Length": str(stat.st_size),
    }

    header_bytes = build_response("", 200, headers)
    # Return header_bytes and file path to be streamed
    return header_bytes, requested_fs_path

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

    #static handling
    static_result = serve_static(request)

    if static_result is not None:
    
        # Static result returns:
        #  (header_bytes, file_path)
        header_bytes, file_path = static_result
    
        # If it's a 304 or error response:
        if file_path is None:
            client_socket.sendall(header_bytes)
            client_socket.close()
            continue
    
        # Send header first
        client_socket.sendall(header_bytes)
    
        # Now stream file in chunks
        try:
            with open(file_path, "rb") as f:
                while True:
                    chunk = f.read(16384)  # 16 KB
                    if not chunk:
                        break
                    client_socket.sendall(chunk)
        except:
            pass
    
        client_socket.close()
        continue

    else:
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
    client_socket.sendall(response)
    client_socket.close()