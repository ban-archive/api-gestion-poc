from ban.commands import command
from ban.http.api import app


@command
def run(port=5959, host='0.0.0.0', **kwargs):
    """Run BAN server (for demo and dev only)."""
    app.run(host, port, debug=True)
