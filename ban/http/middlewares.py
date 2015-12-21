from ban.core import context


class CorsMiddleware:

    def process_response(self, req, resp, resource):
        resp.set_header('X-Powered-By', 'Your Beloved State')
        resp.set_header('Access-Control-Allow-Origin', '*')
        resp.set_header('Access-Control-Allow-Headers', 'X-Requested-With')


class SessionMiddleware:

    def process_response(self, req, resp, resource):
        context.set('session', None)
