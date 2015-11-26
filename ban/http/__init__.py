from wsgiref import simple_server


from ban.http.wsgi import application
from ban.http.resources import *  # noqa
from ban.http.diff import Diff  # noqa
from ban.http.routing import reverse  # noqa

if __name__ == '__main__':
    httpd = simple_server.make_server('127.0.0.1', 5959, application)
    httpd.serve_forever()
