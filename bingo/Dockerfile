ARG POSTGRES_VERSION=17.6
ARG ROCKY_VERSION=9
ARG BINGO_VERSION=1.34.0

FROM alpine:latest AS loader
ARG POSTGRES_VERSION
ARG BINGO_VERSION
# install unzip tar and wget
RUN apk --no-cache add bash wget tar unzip
WORKDIR /tmp

RUN POSTGRES_MAJOR_VERSION=$(echo ${POSTGRES_VERSION} | cut -d. -f1) && \
    wget -O bingo-postgres.zip https://lifescience.opensource.epam.com/downloads/bingo-${BINGO_VERSION}/bingo-postgres-${POSTGRES_MAJOR_VERSION}-linux-x86_64.zip

RUN unzip bingo-postgres.zip && rm bingo-postgres.zip && \
    mv bingo*tgz bingo-postgres.tgz && \
    tar -xvzf bingo-postgres.tgz && rm bingo-postgres.tgz && \
    mv bingo* bingo-postgres


FROM rockylinux:${ROCKY_VERSION}
ARG POSTGRES_VERSION
ARG BINGO_VERSION
ARG POSTGRES_MAJOR_VERSION

LABEL org.opencontainers.image.title="Bingo PostgreSQL" \
    org.opencontainers.image.description="PostgreSQL image with Bingo extension pre-installed" \
    org.opencontainers.image.vendor="Cheminfo" \
    org.opencontainers.image.version="${BINGO_VERSION}" \
    org.opencontainers.image.licenses="Apache-2.0"

# Install PostgreSQL and dependencies
RUN set -eux; \
    POSTGRES_MAJOR_VERSION=$(echo ${POSTGRES_VERSION} | cut -d. -f1); \
    ARCH=$(uname -m); \
    case "${ARCH}" in \
    x86_64) PGDG_ARCH='x86_64' ;; \
    aarch64|arm64) PGDG_ARCH='aarch64' ;; \
    *) echo "Unsupported architecture: ${ARCH}" && exit 1 ;; \
    esac; \
    dnf install -y "https://download.postgresql.org/pub/repos/yum/reporpms/EL-9-${PGDG_ARCH}/pgdg-redhat-repo-latest.noarch.rpm"; \
    dnf -qy module disable postgresql; \
    dnf install -y \
    glibc-langpack-en \
    postgresql${POSTGRES_MAJOR_VERSION}-server \
    postgresql${POSTGRES_MAJOR_VERSION}-contrib; \
    dnf clean all

# Configure PostgreSQL to listen on all interfaces (adapted from official postgres image)
RUN set -eux; \
    POSTGRES_MAJOR_VERSION=$(echo ${POSTGRES_VERSION} | cut -d. -f1); \
    PGSQL_SHARE_DIR="/usr/pgsql-${POSTGRES_MAJOR_VERSION}/share"; \
    # Create a backup of the original config \
    cp -v "${PGSQL_SHARE_DIR}/postgresql.conf.sample" "${PGSQL_SHARE_DIR}/postgresql.conf.sample.orig"; \
    # Modify listen_addresses to accept connections from any IP \
    sed -ri "s!^#?(listen_addresses)\s*=\s*\S+.*!\1 = '*'!" "${PGSQL_SHARE_DIR}/postgresql.conf.sample"; \
    # Verify the change was successful \
    grep -F "listen_addresses = '*'" "${PGSQL_SHARE_DIR}/postgresql.conf.sample"

# Install gosu manually
RUN set -eux; \
    GOSU_VERSION=1.19; \
    GOSU_ARCH="$(uname -m)"; \
    case "${GOSU_ARCH}" in \
    x86_64) GOSU_ARCH='amd64' ;; \
    aarch64) GOSU_ARCH='arm64' ;; \
    *) echo "Unsupported architecture: ${GOSU_ARCH}" && exit 1 ;; \
    esac; \
    curl -fsSL "https://github.com/tianon/gosu/releases/download/${GOSU_VERSION}/gosu-${GOSU_ARCH}" -o /usr/local/bin/gosu; \
    curl -fsSL "https://github.com/tianon/gosu/releases/download/${GOSU_VERSION}/gosu-${GOSU_ARCH}.asc" -o /usr/local/bin/gosu.asc; \
    export GNUPGHOME="$(mktemp -d)"; \
    gpg --batch --keyserver hkps://keys.openpgp.org --recv-keys B42F6819007F00F88E364FD4036A9C25BF357DD4; \
    gpg --batch --verify /usr/local/bin/gosu.asc /usr/local/bin/gosu; \
    gpgconf --kill all; \
    rm -rf "$GNUPGHOME" /usr/local/bin/gosu.asc; \
    chmod +x /usr/local/bin/gosu; \
    gosu --version; \
    gosu nobody true

# Create postgres user and required directories (postgres user is created by PostgreSQL installation)
RUN mkdir -p /var/lib/postgresql /var/run/postgresql /docker-entrypoint-initdb.d && \
    chown -R postgres:postgres /var/run/postgresql /var/lib/postgresql

# Copy entrypoint script
COPY entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/entrypoint.sh && \
    ln -s /usr/local/bin/entrypoint.sh /docker-entrypoint.sh

# Copy Bingo extension files
COPY --from=loader /tmp/bingo-postgres* /opt/bingo-postgres

# Install Bingo extension
RUN POSTGRES_MAJOR_VERSION=$(echo ${POSTGRES_VERSION} | cut -d. -f1) && \
    cd /opt/bingo-postgres && \
    sh ./bingo-pg-install.sh -libdir /opt/bingo-postgres/lib -y && \
    cp ./bingo_install.sql /docker-entrypoint-initdb.d/ && \
    chown postgres:postgres /opt/bingo-postgres/lib/libbingo-postgres.so && \
    cp -p /opt/bingo-postgres/lib/libbingo-postgres.so /usr/pgsql-${POSTGRES_MAJOR_VERSION}/lib/bingo_postgres.so

# Set environment variables
ENV PG_MAJOR=${POSTGRES_MAJOR_VERSION} \
    PATH="/usr/pgsql-${POSTGRES_MAJOR_VERSION}/bin:$PATH" \
    PGDATA=/var/lib/postgresql/data \
    LANG=en_US.UTF-8

WORKDIR /var/lib/postgresql

VOLUME ["/var/lib/postgresql/data"]

STOPSIGNAL SIGINT

EXPOSE 5432

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD pg_isready -U postgres


ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["postgres"]