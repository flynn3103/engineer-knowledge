# Containers and Docker — Junior

<!-- level-focus -->
At junior level, focus on this question:

> Given a small application, can you write a Dockerfile that builds a working image and reliably reproduces it as a running container, explaining what each instruction does?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

---

## Core Concept 1 — Vocabulary: Image, Container, Registry, Dockerfile

Four words get used loosely. Keep them apart:

- **Dockerfile** — a text file of instructions that describes how to build an image: which base to start from, what to copy in, what to install, what to run.
- **Image** — the built, read-only result of running a Dockerfile through `docker build`. An image is a stack of layers plus metadata (default command, exposed ports, environment). It does nothing by itself; it's a template.
- **Container** — a running instance of an image. Starting a container adds a thin writable layer on top of the image's read-only layers and gives the process its own filesystem view, network namespace, and process tree. You can start many containers from the same image.
- **Registry** — a server that stores and serves images by name and tag (for example `docker.io/library/python:3.12-slim` or a private registry like `ghcr.io/your-org/app:1.4.0`). `docker pull` fetches from a registry; `docker push` publishes to one.

The relationship in one line: **a Dockerfile builds an image, an image runs as a container, and a registry is where images live between builds and runs.**

## Core Concept 2 — Anatomy of a Dockerfile

A minimal but realistic Dockerfile for a small Python web service:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["python", "app.py"]
```

Each instruction, in order:

| Instruction | What it does |
|---|---|
| `FROM python:3.12-slim` | Picks the base image everything else builds on top of — here, a slimmed-down Debian with Python 3.12 preinstalled |
| `WORKDIR /app` | Sets the working directory inside the image for every instruction that follows; creates it if it doesn't exist |
| `COPY requirements.txt .` | Copies one file from your build context into the image |
| `RUN pip install ...` | Executes a command *during the build*, baking its result (installed packages) into a layer |
| `COPY . .` | Copies the rest of the application source into the image |
| `EXPOSE 8000` | Documents that the container listens on port 8000 — this is metadata only, it does **not** publish the port |
| `CMD ["python", "app.py"]` | The default command a container runs when started, unless overridden |

Note the two separate `COPY` steps instead of one `COPY . .` at the top — that ordering choice is explained in Core Concept 4, and it is the single most common thing junior Dockerfiles get backwards.

## Core Concept 3 — The Build-and-Run Cycle

Four commands cover almost everything you need at this level:

```bash
# Build an image from the Dockerfile in the current directory, tagging it
docker build -t hello-service:1.0 .

# List images you have locally
docker images

# Run a container from the image, mapping host port 8000 to container port 8000
docker run -d -p 8000:8000 --name hello hello-service:1.0

# List running containers
docker ps
```

Sample output after building and running:

```
$ docker build -t hello-service:1.0 .
[+] Building 4.2s (10/10) FINISHED
 => [1/4] FROM docker.io/library/python:3.12-slim
 => [2/4] WORKDIR /app
 => [3/4] COPY requirements.txt .
 => [4/4] RUN pip install --no-cache-dir -r requirements.txt
 => exporting to image
 => naming to docker.io/library/hello-service:1.0

$ docker run -d -p 8000:8000 --name hello hello-service:1.0
a1b2c3d4e5f6

$ docker ps
CONTAINER ID   IMAGE                 STATUS         PORTS                    NAMES
a1b2c3d4e5f6   hello-service:1.0     Up 3 seconds   0.0.0.0:8000->8000/tcp   hello

$ curl localhost:8000/health
{"status":"ok"}
```

The `-p 8000:8000` flag is doing the actual work that `EXPOSE` only documented: it publishes the container's port 8000 onto the host's port 8000. Forget `-p` and `EXPOSE` alone will not make the service reachable from outside the container.

Two more commands you'll reach for constantly while developing:

```bash
docker logs hello          # see what the process printed to stdout/stderr
docker exec -it hello sh   # get a shell inside the running container
docker stop hello          # ask the container to stop
docker rm hello            # remove the stopped container
```

## Core Concept 4 — Layers and Why Instruction Order Matters

Every `FROM`, `COPY`, and `RUN` instruction creates a **layer** — a filesystem diff, cached and stacked on top of the layers before it. When you rebuild, Docker reuses a cached layer as long as the instruction and everything it depends on (the files it copies, the command it runs) haven't changed. The first instruction that *does* change invalidates every layer after it, forcing a rebuild from that point down.

This is why the Dockerfile in Core Concept 2 copies `requirements.txt` and installs dependencies *before* copying the rest of the source code:

```mermaid
flowchart LR
    A[FROM python:3.12-slim] --> B[COPY requirements.txt]
    B --> C[RUN pip install]
    C --> D[COPY . .]
    D --> E[CMD python app.py]
```

Application source code (`app.py`, templates, etc.) changes on nearly every commit. Dependency lists (`requirements.txt`, `package.json`) change rarely. Copying the rarely-changing file first means the expensive `pip install` layer stays cached across most builds — only the cheap `COPY . .` layer at the bottom is rebuilt. Flip the order — `COPY . .` before installing dependencies — and *every* source change invalidates the install step too, turning a two-second cached build into a minute-long reinstall every time.

You can inspect an image's layers directly:

```bash
docker history hello-service:1.0
```

```
IMAGE          CREATED BY                                      SIZE
f4a8b2c1d3e5   CMD ["python" "app.py"]                          0B
9d8e7f6a5b4c   COPY . .                                         2.1kB
7c6b5a4d3e2f   RUN pip install --no-cache-dir -r requirements…  18.4MB
3a2b1c0d9e8f   COPY requirements.txt .                          31B
1e2d3c4b5a6f   WORKDIR /app                                     0B
...
```

## Core Concept 5 — .dockerignore

By default, `docker build` sends your *entire* current directory to the Docker daemon as the "build context," even files you never `COPY`. A `.dockerignore` file excludes what shouldn't be sent — this keeps the build fast and prevents accidentally baking secrets or bloat into an image:

```
.git
__pycache__/
*.pyc
.env
node_modules/
```

Without it, a stray `.env` file with real credentials sitting next to your Dockerfile can end up copied into an image layer by an overly broad `COPY . .` — and once it's in a layer, it's in the image, even if a later layer deletes the file (Core Concept covered more in the senior guide).

## Common Mistakes

1. **Using `FROM python:latest` (or any `:latest` tag).** `latest` is just another tag, not "the newest stable version" — it can point to a different, breaking version tomorrow. Pin a specific version tag (`python:3.12-slim`) so a rebuild next month uses the same base you tested against.

2. **Copying source before installing dependencies.** As shown in Core Concept 4, this throws away layer caching and makes every build reinstall every dependency, turning fast iterative builds into slow ones.

3. **Forgetting `EXPOSE` doesn't publish anything.** `EXPOSE` is documentation for humans and other tooling; the port is only actually reachable from the host when you pass `-p host:container` to `docker run`.

4. **Confusing `CMD` with `RUN`.** `RUN` executes once, at build time, and its result is baked into the image. `CMD` defines what runs when a container *starts*. Putting your application's start command in `RUN` builds an image that does nothing when you run it.

5. **Skipping `.dockerignore`.** A missing `.dockerignore` sends your whole working directory — including `.git`, virtual environments, and local secrets — into the build context, slowing builds and risking secrets ending up in a layer.

6. **Not cleaning up stopped containers and dangling images.** `docker ps` only shows running containers; `docker ps -a` shows everything, and stopped containers and unused images accumulate disk space until you `docker rm`/`docker rmi` (or `docker system prune`) them.

## Apply it

1. Write a small HTTP service (any language you know) with one `/health` endpoint that returns `{"status":"ok"}`, and a dependency manifest file (`requirements.txt`, `package.json`, or equivalent).
2. Write a Dockerfile for it following the order in Core Concept 2: pin the base image tag, copy the dependency manifest and install dependencies *before* copying the rest of the source, then set `CMD` to start the service.
3. Add a `.dockerignore` that excludes your VCS directory and any local dependency caches.
4. Build the image with `docker build -t <name>:1.0 .`, run it with `docker run -d -p 8000:8000 --name <name> <name>:1.0`, and confirm `curl localhost:8000/health` returns the expected JSON.
5. Change one line in your source file only (not the dependency manifest), rebuild, and use `docker history` or the build output to confirm the dependency-install layer was reused from cache while only the source-copy layer rebuilt.

## Verify your work

- `docker images` lists your image with the tag you built.
- `docker ps` shows the container in the `Up` state with the port mapping you specified.
- `curl localhost:8000/health` (or your chosen port) returns the expected response from outside the container.
- After changing only application source and rebuilding, the build output shows the dependency-install step reusing cache (`CACHED` in the build log) rather than reinstalling.
- `docker logs <name>` shows your application's startup output with no unexpected errors.

## Review questions

- What is the difference between an image and a container?
- Why does `EXPOSE` in a Dockerfile not make a service reachable from the host by itself?
- Why does copying a dependency manifest and installing dependencies before copying the rest of the source code speed up rebuilds?
- What is the practical risk of building `FROM` a `:latest` tag instead of a pinned version?
