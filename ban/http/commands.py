"""Expose some commands as API endpoints"""
from io import StringIO
from ban.commands.bal import bal
from ban.core import context

from .wsgi import app
from .auth import auth


class Import:

    @auth.protect
    @app.endpoint(path='/bal')
    def on_post_bal(self, req, resp, *args, **kwargs):
        """Import file at BAL format.

        responses:
            200:
                description: File has been processed.
        """
        data = req.get_param('data', required=True)
        bal(StringIO(data.value.decode('utf-8-sig')))
        reporter = context.get('reporter')
        resp.json(report=reporter)

app.register_resource(Import())
