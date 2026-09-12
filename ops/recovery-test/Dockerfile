FROM postgres:16-alpine

COPY verify.sh /usr/local/bin/verify-recovery.sh
RUN chmod 755 /usr/local/bin/verify-recovery.sh

CMD ["/usr/local/bin/verify-recovery.sh"]
