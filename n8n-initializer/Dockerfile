FROM alpine:latest

RUN apk add --no-cache curl bash jq

COPY init-n8n.sh /init-n8n.sh
RUN chmod +x /init-n8n.sh

CMD ["/init-n8n.sh"]