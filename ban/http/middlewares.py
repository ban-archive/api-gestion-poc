from ban.core import context


class CorsMiddleware:

    def process_response(self, req, resp, resource):
        resp.set_header('X-Powered-By', 'Your Beloved State')
        resp.set_header('Access-Control-Allow-Origin', '*')
        resp.set_header('Access-Control-Allow-Headers', 'X-Requested-With')


class RouteMiddleware:
    # Use me when https://github.com/falconry/falcon/pull/651 get merged.

    def process_resource(self, req, resp, resource, params):
        if 'id' in params:
            *identifier, id = params['id'].split(':')
            params['identifier'] = identifier[0] if identifier else 'id'
            params['id'] = id


class SessionMiddleware:

    def process_response(self, req, resp, resource):
        context.set('session', None)
