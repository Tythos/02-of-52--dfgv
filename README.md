"Stack" is a loaded term. I did a substantial amount of development in college and grad school (both professionally and for a variety of personal projects) with the classic "LAMP" stack (Linux, Apache, MySQL, and PHP), and even today there's no denying that's [a potent combination of tools](https://www.youtube.com/watch?v=WsnHWxO7Krw). But there's far too many combinations of technology clamoring to be "the new LAMP" equivalent (usually chasing the hot new thing) and I'll be honest, I'm not buying it.

_(That having been said, I wouldn't mind giving this recent [HTMX+Go+Tailwind](https://medium.com/gravel-engineering/go-htmx-tailwind-create-beautiful-responsive-web-apps-without-javascript-sort-of-3d096c57524b) trend a try.)_

I approached the problem from the opposite perspective. What combinations of technologies have I actually found myself using to solve a wide number of problems? A lot of these have been professional, but the specific "stack" in this case translates very well to side projects. It's handy for any effort where it's important to keep your project "self-contained" for deployment, stability, or integration into a larger orchestrated solution.

![Guilty as charged](https://dev-to-uploads.s3.amazonaws.com/uploads/articles/79z9i2gfkgy1df2h061q.jpg)

## The Container

Since we want something self-contained that can be built, moved, and deployed (or orchestrated or scaled) anywhere, we'll focus on a single-container application. But what goes "into" an application? Let's consider two sets of code:

1. Front-end code, which we'll use to define the client consuming our server capabilities. HTML/CSS/JS seems the logical choice here, which is probably no surprise. But in the interest of avoiding framework lock-in, we'll use Vite as a basic bundler to serve static HTML. The important part here is, as far as the server is concerned, the front-end code is merely a set of static files that need to be exposed on a route.

2. Back-end code, which will define the server behavior. I dislike the server-side rendering approach taken by PHP--you have a client that can run instructions within a well-defined browser environment, take advantage of it! Instead, server-side endpoints will focus on logic-driven responses (and a few additions we'll consider later). This will ideally come within a well-defined set of endpoints, hosted by a production-grade asynchronous server.

I'm bringing this up because we want to consider how our container will be constructed. Sneak peak: since the "f" and "g" in our acronym stand for "Flask" and "Gevent", you've probably already figured out this will be Python-driven. So, let's start with a one-line Docker container based on a Python distribution:

```Dockerfile
FROM python3.11
```

## The Backend

Flask is a thing of beauty. I really appreciate tools that let you use as little as you need, and (while there are substantial toolsets built around Flask itself) using Flask simply to define a set of routes wrapped into a WSGI application is a fantastic use case.

Let's define a basic "root" or index endpoint in a new file, `server.py`. This is pretty bare-bones but we'll flesh it out later.

```py
"""
Our server
"""

import os
import flask

PACK_PATH, _ = os.path.split(os.path.abspath(__file__))
_, PACK_NAME = os.path.split(PACK_PATH)
APP = flask.Flask(PACK_NAME)

@APP.route("/", methods=["GET"])
def index():
    """
    Basic 'root' endpoint
    """
    return b"Whazzup", 200, {
        "Content-Type": "text-plain"
    }
```

This returns some bytes with a `200 OK` status as plain text. I find it's useful to make a habit of explicitly declaring HTTP methods, status codes, and content type when your backend is focused on procedural responses. It makes it easy to swap out, extend, and identify specific behaviors, particularly when testing and growing the code

## The Server

We've defined a WSGI application (did you know the result of a Flask constructor is interchangable with WSGI handlers?), but we haven't defined how it will be served. There is a testing server built into Flask but (as it is not shy about telling you) it isn't production-grade, largely related to its synchronous nature.

It's also fairly limited--specifically, it's not compatible with a variety of other extensions and protocols we might want to support. Instead, after trying a wide variety of alternatives, I've found myself biased towards Gevent:

* It works well with Flask

* It supports asynchronous scaling out of the box

* It is platform-neutral

* It is compatible with WSGI

* It supports a variety of other handlers that you can import & mix-and-match as needed

It's also native Python so our container remains consolidated without worrying about patching configurations from (for example) nginx or Apache. Plugging Gevent into our `server.py` file is very straightforward. In addition to the extra `import`, we'll add a `main()` method that is called whenever the script is run directly.

```py
from gevent import pywsgi

# ... previous imports go here

SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8000"))

# ... previous code goes here

def main():
    """
    Hosts the Flask-defined WSGI application with Gevent
    """
    print("Hosting %s at %s:%u" % (PACK_NAME, SERVER_HOST, SERVER_PORT))
    pywsgi.WSGIServer((SERVER_HOST, SERVER_PORT), APP).serve_forever()

if __name__ == "__main__":
    main()
```

We do need to define our dependencies. Short of [going full `TOML`](https://hitchdev.com/strictyaml/why-not/toml/) on you, let's just capture our Python packages in a `requirements.txt`:

```txt
flask
gevent
```

You can test both files by installing, then running, the server directly:

```sh
$ pip install -r requirements.txt
$ python server.py
```

You should see a message, after which a quick `curl` against the appropriate address will confirm it is functioning as intended:

```sh
$ curl localhost:8000
Whazzup
```

# The Front End

Create a `public/` subfolder within our project. Within that folder, we'll use Yarn to set up a basic vanilla Vite project as it's own self-contained Node package. This can be done with a single command:

```sh
$ yarn create vite . --template vanilla
```

(You may need to install yarn and vite globally if you don't already have them exposed on your system.)

We can now "pack" our application by installing dependencies and building it into a set of static files:

```sh
$ yarn install
$ yarn run build
```

In the long run, building the Vite application could be done by your CI process and/or within the Dockerfile steps. For now we'll run it ourselves and be happy with our little static files stack that results. Now we need to point our server to this path, so go back and edit `server.py` to add a new endpoint:

```py
@APP.route("/<path:path>", methods=["GET"])
def public(path):
    """
    Routes static file requests
    """
    return flask.send_from_directory(PACK_PATH + "/public/dist", path)
```

This instructs Flask to route any static files matching the requested path to the `public/dist` folder within our Vite application build. But the astute among you may also notice we need to redefine the "index" endpoint to route to the base HTML page, so let's modify that part of our `server.py` file now too:

```py
@APP.route("/", methods=["GET"]))
def index(): 
    """
    Basic 'root' endpoint
    """
    return flask.send_file(PACK_PATH + "/public/dist/index.html")
```

You can now try to "run" the server again locally:

```sh
$ python server.py
```

Browsing to "http://localhost:8000", you should see the boilerplate Vite application! Pretty cool. We're just about done.

![Image description](https://dev-to-uploads.s3.amazonaws.com/uploads/articles/apjkv86pnipiw3wq5l24.png)

## Putting It All Together

Our Dockerfile is still pretty minimal. Even assuming the Vite bundling takes place separately, we still need to extend the base Python image to ensure our container will build a self-contained application. This takes the form of several steps:

1. First, we need to define a "working directory" where (within the container filesystem) our application will "run".

2. Next, we need to copy the contents of our project into this working directory.

3. Then, we need to use pip to install the Python dependencies from the "requirements.txt" file we defined.

4. Lastly, we need to identify the server (run with Python) as the 
"entry point" launched when the container is started from our image.

Within our `Dockerfile`, this will look something like this (including our single line from earlier):

```Dockerfile
FROM python:3.11
WORKDIR /app
COPY . .
RUN ["pip", "install", "-r", "requirements.txt"]
ENTRYPOINT ["python", "server.py"]
```

You should then be able to run a `docker build` command from your terminal. With an appropriate tag, you can now publish and share your application with the world--not to mention spin it up to server it anywhere you want!

![Stack architecture diagram](https://dev-to-uploads.s3.amazonaws.com/uploads/articles/o00thrg6z4nyxhhi1omh.png)

## Next Steps

This is a great "pattern" of a stack, largely because of a) how much it gives you "out of the box", and b) how much you can do by extending it incrementally to include new capabilities without worrying too much about how well it will deploy, how the client-server state will be managed, etc. You can check the source here:

[https://github.com/Tythos/dfgv](https://github.com/Tythos/dfgv)

And if you're not reading it already there's an article up on dev.to as well:

[https://dev.to/tythos/dfgv-self-contained-full-stack-web-apps-32fj](https://dev.to/tythos/dfgv-self-contained-full-stack-web-apps-32fj)

Let's consider some potential questions and issues, though:

### But What About Data/State!?

In the traditional "LAMP" stack, state on the backend was consolidated within the "M" (a MySQL database). We don't have a data tool hard-coded into this stack. What we *do* have is a flexible Python server that can identify specific endpoints to "hook" into whatever backend is needed.

This could take the shape of a volume mount (we are running in a Docker container, after all) from an external file system (or stateful set from Kubernetes, etc.); a database service (installed/running locally or connected to from Python; or any other data source that Python (and/or Flask itself) can reach out to. You aren't limited to anything in particular, and the Flask endpoints can leverage anything with Python support simply by adding a package dependency.

This is a good point to talk about configuration synchronization, though. You'll notice some `os.getenv()` calls in our `server.py` source. You should be loading specific configuration information--whether it's the port to server on, the database connection string, or any other useful deployment parameters--from environmental variables that can be specifically assigned from whatever context you are deploying your image--be it an .ENV file, docker-compose settings, or a configmap within Kubernetes. The `os.getenv()` pattern, though, gives you a good way to ensure some degree of defaults are always available.

### Why Can't We Build It All At Once!?

Vite gives us a great compromise between static vanilla web application files and something that can be "built" in a managed fashion from more complex frameworks. But fundamentally it's still a server-side JavaScript framework (just one that needs to be run "once" to build the static files). So, building it as part of our `docker build .` command would require a few modifications.

Since our "base" image in the above examples is "python:3.11", we'd want to change this to a tag that indicates a specific system (like Alpine). This would ensure we have a package manager to install Node and any requisite dependencies (like yarn). Finally, we would want to call the "build" script for this package as part from within the `Dockerfile`.

I kept it simple because there are other ways you may want to go about this. You may want to manage the application separately (within another repository, perhaps) and hook it in as a submodule or some other managed artifact. You may also want to call it from a CI script, or add intermediate build products to a `.dockerignore` so only the static files get moved into the deployment image with the `COPY * *` command. Finally, you may want to combine multiple base containers (it's possible!) for different build passes to use a Node base image directly for the frontend.

![Too much for you?](https://dev-to-uploads.s3.amazonaws.com/uploads/articles/dykiano49h1kwh6fjakk.jpg)

### What's So Great About Gevent Anyway!?

I've been tip-toeing around some of the specific reasons I typically go with Gevent (after many painful experiences with other approaches). I've mentioned a few other reasons already, but I'd also like to call out two additional "follow-on" considerations:

1. The integration with WebSocket listeners by Gevent is fantastic and mostly painless (https://github.com/heroku-python/flask-sockets). You can event bind specific WebSocket connection routes, share a pool of connections for message broadcasting, and treat them as "peer" data pathways within your Flask application. Just thinking about it makes me want to write a follow-on article! It really is that slick.

2. Gevent can "monkey-patched" asynchronous core behaviors that help Python be a much more suitable production-grade environment for web servers that it would otherwise be. Who knows, maybe this will no longer be necessary once 3.14 gets rid of the GIL (https://realpython.com/python-gil/)! But in the meantime, Gevent's greenlet-based approach works very well.
