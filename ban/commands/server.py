from wsgiref.simple_server import make_server

from ban.commands import command
from ban.http import application


@command
def run(port=5959, host='0.0.0.0', **kwargs):
    """Run BAN server (for demo and dev only)."""
    httpd = make_server(host, port, application)
    print("Serving HTTP on {}:{}...".format(host, port))
    try:
        httpd.serve_forever()
    except (KeyboardInterrupt, EOFError):
        print('Bye!')
