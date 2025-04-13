FROM nginx:latest

# Install necessary tools
RUN apt-get update && apt-get install -y openssl curl

# Create directories
RUN mkdir -p /var/cache/nginx/proxy_cache
RUN mkdir -p /var/cache/nginx/api_cache
RUN mkdir -p /var/cache/nginx/external_cache
RUN mkdir -p /etc/nginx/certs
RUN mkdir -p /usr/share/nginx/html

# Copy index.html
COPY index.html /usr/share/nginx/html/index.html

# Create health check file
RUN echo "healthy" > /usr/share/nginx/html/health

# Copy configuration files
COPY nginx.conf /etc/nginx/nginx.conf
COPY conf.d/ /etc/nginx/conf.d/

# Generate self-signed certificate for localhost
RUN openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/nginx/certs/nginx.key \
    -out /etc/nginx/certs/nginx.crt \
    -subj "/C=US/ST=State/L=City/O=GroundedLLM/CN=localhost"

# Generate DH parameters for improved security
RUN openssl dhparam -out /etc/nginx/certs/dhparam.pem 2048

# Set proper permissions for certificates
RUN chmod 644 /etc/nginx/certs/nginx.crt \
    && chmod 600 /etc/nginx/certs/nginx.key \
    && chmod 644 /etc/nginx/certs/dhparam.pem

# Expose ports
EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"]
