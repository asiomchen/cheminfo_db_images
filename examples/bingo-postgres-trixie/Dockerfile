FROM ghcr.io/asiomchen/bingo-dist:1.43.0-postgres17 AS bingo_dist

FROM postgres:17-trixie

COPY --from=bingo_dist /out/bingo-postgres.tgz /tmp/bingo-postgres.tgz

RUN set -eux; \
    mkdir -p /opt/bingo-postgres /docker-entrypoint-initdb.d; \
    tar -xzf /tmp/bingo-postgres.tgz -C /opt/bingo-postgres --strip-components=1; \
    cd /opt/bingo-postgres; \
    sh ./bingo-pg-install.sh -libdir /opt/bingo-postgres/lib -y; \
    install -m 0644 ./bingo_install.sql /docker-entrypoint-initdb.d/bingo_install.sql; \
    rm -f /tmp/bingo-postgres.tgz
