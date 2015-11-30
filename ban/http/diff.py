from ban.core import versioning
from .wsgi import app
from .auth import auth
from .resources import BaseCollection


class Diff(BaseCollection):

    @auth.protect
    def on_get(self, req, resp, *args, **kwargs):
        """Get database diffs.

        Query parameters:
        increment   the minimal increment value to retrieve
        """
        qs = versioning.Diff.select()
        increment = req.get_param_as_int('increment')
        if increment:
            qs = qs.where(versioning.Diff.id > increment)
        self.collection(req, resp, qs.as_resource())


app.register_resource(Diff())
