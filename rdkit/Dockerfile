ARG ROCKY_VERSION=9
ARG RDKIT_DIST_IMAGE=ghcr.io/asiomchen/rdkit-postgres-dist:2025.09.5-postgres17

FROM ${RDKIT_DIST_IMAGE} AS loader
RUN mkdir -p /tmp && \
    tar -xvzf /out/rdkit-postgres.tgz -C /tmp && \
    mv /tmp/rdkit-postgres* /tmp/rdkit-postgres

FROM rockylinux:${ROCKY_VERSION}
ARG POSTGRES_VERSION
ARG POSTGRES_MAJOR_VERSION
ARG RDKIT_GIT_REF

LABEL org.opencontainers.image.title="RDKit PostgreSQL" \
    org.opencontainers.image.description="PostgreSQL image with RDKit extension pre-installed" \
    org.opencontainers.image.vendor="Cheminfo" \
    org.opencontainers.image.version="${RDKIT_GIT_REF}" \
    org.opencontainers.image.licenses="BSD-3-Clause" \
    org.opencontainers.image.source="https://github.com/asiomchen/cheminfo_db_images"

# Install Runtime dependencies and PostgreSQL
RUN set -eux; \
    POSTGRES_MAJOR_VERSION=$(echo ${POSTGRES_VERSION} | cut -d. -f1); \
    dnf install -y epel-release; \
    dnf config-manager --set-enabled crb; \
    dnf install -y https://download.postgresql.org/pub/repos/yum/reporpms/EL-9-$(uname -m)/pgdg-redhat-repo-latest.noarch.rpm; \
    dnf -qy module disable postgresql; \
    dnf install -y \
    bzip2-libs \
    freetype \
    zlib \
    xz \
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
    # Add rdkit to shared_preload_libraries \
    sed -ri "s!^#?(shared_preload_libraries)\s*=\s*\S+.*!\1 = 'rdkit'!" "${PGSQL_SHARE_DIR}/postgresql.conf.sample"; \
    # Verify the changes were successful \
    grep -F "listen_addresses = '*'" "${PGSQL_SHARE_DIR}/postgresql.conf.sample"; \
    grep -F "shared_preload_libraries = 'rdkit'" "${PGSQL_SHARE_DIR}/postgresql.conf.sample"


# Install gosu
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

# Create postgres user and directories
RUN mkdir -p /var/lib/postgresql /var/run/postgresql /docker-entrypoint-initdb.d && \
    echo "CREATE EXTENSION IF NOT EXISTS rdkit;" > /docker-entrypoint-initdb.d/rdkit.sql && \
    chown -R postgres:postgres /var/run/postgresql /var/lib/postgresql /docker-entrypoint-initdb.d

# Copy artifacts from RDKit distribution image
COPY --from=loader /tmp/rdkit-postgres /opt/rdkit-postgres

RUN POSTGRES_MAJOR_VERSION=$(echo ${POSTGRES_VERSION} | cut -d. -f1) && \
    cd /opt/rdkit-postgres && \
    sh ./rdkit-pg-install.sh \
      -libdir /usr/pgsql-${POSTGRES_MAJOR_VERSION}/lib \
      -sharedir /usr/pgsql-${POSTGRES_MAJOR_VERSION}/share/extension \
      -y

# Set environment variables
ENV PG_MAJOR=${POSTGRES_MAJOR_VERSION}
ENV PATH="/usr/pgsql-${POSTGRES_MAJOR_VERSION}/bin:$PATH"
ENV PGDATA=/var/lib/postgresql/data
ENV LANG=en_US.UTF-8

COPY entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/entrypoint.sh && \
    ln -s /usr/local/bin/entrypoint.sh /docker-entrypoint.sh

WORKDIR /var/lib/postgresql

VOLUME ["/var/lib/postgresql/data"]

STOPSIGNAL SIGINT
EXPOSE 5432

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD pg_isready -U postgres

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["postgres"]
