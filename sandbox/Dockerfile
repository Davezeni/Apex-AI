# Multi-language sandbox: runs agent-generated code in isolation.
# Includes Node, Python, and Go toolchains so the agent can scaffold and run
# apps in multiple languages. (Rust omitted — heavy build; add if needed.)
FROM node:20-alpine

RUN apk add --no-cache \
    python3 py3-pip git curl zip \
    go \
    && ln -sf python3 /usr/bin/python

WORKDIR /workspace

# Keep the container alive for `docker exec` access.
CMD ["tail", "-f", "/dev/null"]
