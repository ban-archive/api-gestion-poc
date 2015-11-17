from ban.core import versioning
from .wsgi import app
from .auth import auth
from .resources import BaseCollection


class Diff(BaseCollection):

    @auth.protect
    def on_get(self, req, resp, *args, **kwargs):
        self.collection(req, resp, versioning.Diff.select().as_resource())


app.add_route('/diff', Diff())
