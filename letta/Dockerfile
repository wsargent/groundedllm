FROM letta/letta:0.7.28

# Copy Caddy's self-signed certificate
# The build context is the project root (.), so caddy/ refers to the project's caddy directory
COPY ./caddy/ca.pem /usr/local/share/ca-certificates/mkcert-ca.crt

# Install CA certificates package and update the system's trust store
# This assumes the base image is Debian-based.
RUN apt-get update && \
    apt-get install -y --no-install-recommends ca-certificates && \
    update-ca-certificates && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
