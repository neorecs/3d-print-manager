FROM alpine:3.21

RUN apk add --no-cache restic ca-certificates tzdata

COPY backup-loop.sh /usr/local/bin/backup-loop.sh
RUN sed -i 's/\r$//' /usr/local/bin/backup-loop.sh \
    && chmod 755 /usr/local/bin/backup-loop.sh

CMD ["/bin/sh", "/usr/local/bin/backup-loop.sh"]
