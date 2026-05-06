# Habeas Protocol — reproducible build environment.
#
# Goal: clone the repo, run `docker build -t habeas .`, then
#       `docker run --rm habeas make test` and have all 1930 property
#       invariants + every Catala typecheck/interpret + every conformance
#       test pass — without touching the host.
#
# Sized for `make test`. Postgres + the dashboard are NOT bundled here
# (they're a separate `docker-compose.yml` story); this image is the
# minimum viable rule-runner.

FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

# OS-level deps:
#   - opam + ocaml — Catala compiler dependency
#   - python3 + pip — reference evaluators + property tests
#   - postgresql-client — `psql` CLI used by api/server.py
#   - git — used by some scripts
#   - build-essential, m4, pkg-config, bubblewrap — opam build deps
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        m4 \
        pkg-config \
        bubblewrap \
        unzip \
        curl \
        ca-certificates \
        git \
        sudo \
        opam \
        ocaml \
        ocaml-base-nox \
        libgmp-dev \
        zlib1g-dev \
        libffi-dev \
        ninja-build \
        libpcre3-dev \
        python3 \
        python3-pip \
        postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Catala 1.1.0 via opam — pinned exactly to match CI. Allow opam to
# auto-install system dependencies via apt (depexts) so we don't have to
# track every transitive system package by hand. The `OPAMCONFIRMLEVEL`
# var makes opam answer all interactive prompts (including the apt-install
# confirmation triggered by --depext) with yes.
ENV OPAMCONFIRMLEVEL=unsafe-yes
ENV OPAMYES=1
RUN opam init --disable-sandboxing --bare --reinit -y \
    && opam switch create catala 4.14.2 -y \
    && eval "$(opam env --switch=catala)" \
    && opam install -y --confirm-level=unsafe-yes catala.1.1.0

ENV OPAMROOT=/root/.opam
ENV PATH="/root/.opam/catala/bin:${PATH}"

WORKDIR /app

# Install Python deps first so the layer caches cleanly.
COPY requirements.txt .
RUN pip3 install --break-system-packages --no-cache-dir -r requirements.txt

# Then bring in the project itself.
COPY . .

# Default: run the full test pass. Override with `docker run … <other-cmd>`.
CMD ["bash", "-lc", "eval $(opam env --switch=catala) && make test"]
