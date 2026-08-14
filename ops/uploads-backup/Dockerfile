FROM alpine:3.21

COPY backup-loop.sh /usr/local/bin/backup-loop.sh
RUN chmod 755 /usr/local/bin/backup-loop.sh

CMD ["/bin/sh", "/usr/local/bin/backup-loop.sh"]
