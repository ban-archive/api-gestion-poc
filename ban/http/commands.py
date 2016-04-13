"""Expose some commands as API endpoints"""
from io import StringIO
from ban.commands.bal import bal

from .wsgi import app
from .auth import auth


class Import:

    @auth.protect
    @app.endpoint(path='/bal')
    def on_post_bal(self, req, resp, *args, **kwargs):
        """Import file at BAL format."""
        data = req.get_param('data', required=True)
        bal(StringIO(data.value.decode('utf-8-sig')))

app.register_resource(Import())
