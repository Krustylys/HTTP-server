# HTTP-server

A lightweight and raw Python web framework for building HTTP servers from scratch. This project aims to provide a minimal yet highly flexible base for custom web servers or learning purposes.

## Features

- ⚡ **Lightweight:** Minimal dependencies, fast startup, and low memory footprint.
- 🔧 **Raw and Customizable:** Build your own HTTP logic without complex abstractions.
- 📚 **Educational:** Designed to help you understand HTTP, sockets, and basic web server concepts.
- 🐍 **Pure Python:** No external frameworks required – just standard Python libraries.

## Getting Started

### Requirements

- Python 3.6 or higher

### Installation

Clone this repository:

```bash
git clone https://github.com/Krustylys/HTTP-server.git
cd HTTP-server
```

### Usage

Run the server with:

```bash
python server.py
```

By default, the server will start on `http://localhost:8080`.

You can edit `server.py` to add routes, handlers, or custom logic as needed.

## Example

```python
# server.py
from http.server import BaseHTTPRequestHandler, HTTPServer

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'Hello, World!')
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not Found')

def run(server_class=HTTPServer, handler_class=SimpleHandler, port=8080):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f'Starting HTTP server on port {port}...')
    httpd.serve_forever()

if __name__ == '__main__':
    run()
```

## Contributing

Contributions are welcome! Feel free to open issues or submit pull requests.

## License

This project is licensed under the MIT License.
