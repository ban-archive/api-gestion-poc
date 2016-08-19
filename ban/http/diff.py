from ban.core import versioning
from .wsgi import app
from .auth import auth
from .resources import BaseCollection


class Diff(BaseCollection):

    model = versioning.Diff

    @auth.protect
    @app.endpoint()
    def on_get(self, req, resp, *args, **kwargs):
        """Get database diffs.

        parameters:
        - name: increment
          in: query
          description: The minimal increment value to retrieve
          type: integer
          required: false
        responses:
          200:
            description: A list of diff objects
            schema:
              $ref: '#/definitions/Diff'
        """
        qs = versioning.Diff.select()
        increment = req.get_param_as_int('increment')
        if increment:
            qs = qs.where(versioning.Diff.pk > increment)
        self.collection(req, resp, qs.as_resource())


app.register_resource(Diff())
