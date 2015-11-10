from wsgiref import simple_server


from ban.http.wsgi import application
from ban.http.resources import *  # noqa


if __name__ == '__main__':
    httpd = simple_server.make_server('127.0.0.1', 5959, application)
    httpd.serve_forever()
