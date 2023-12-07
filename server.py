"""
Our server
"""

import os
import flask
from gevent import pywsgi

PACK_PATH, _ = os.path.split(os.path.abspath(__file__))
_, PACK_NAME = os.path.split(PACK_PATH)
APP = flask.Flask(PACK_NAME)
SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8000"))

@APP.route("/", methods=["GET"])
def index():
    """
    Basic 'root' endpoint
    """
    return flask.send_file(PACK_PATH + "/public/dist/index.html")

@APP.route("/<path:path>", methods=["GET"])
def public(path):
    """
    Routes static file requests
    """
    return flask.send_from_directory(PACK_PATH + "/public/dist", path)

def main():
    """
    Hosts the Flask-defined WSGI application with Gevent
    """
    print("Hosting %s at %s:%u" % (PACK_NAME, SERVER_HOST, SERVER_PORT))
    pywsgi.WSGIServer((SERVER_HOST, SERVER_PORT), APP).serve_forever()

if __name__ == "__main__":
    main()
