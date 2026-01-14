ARG ROCKY_VERSION=9
ARG BOOST_VERSION=1.84.0

# Stage 1: Build Boost from source
FROM rockylinux:${ROCKY_VERSION} AS boost-builder
ARG BOOST_VERSION

RUN dnf install -y \
    gcc-c++ \
    make \
    wget \
    tar \
    bzip2 \
    bzip2-devel \
    zlib-devel \
    python3-devel \
    && dnf clean all

WORKDIR /opt
RUN BOOST_VERSION_UNDERSCORE=$(echo ${BOOST_VERSION} | tr . _) && \
    wget https://archives.boost.org/release/${BOOST_VERSION}/source/boost_${BOOST_VERSION_UNDERSCORE}.tar.gz && \
    tar -xzf boost_${BOOST_VERSION_UNDERSCORE}.tar.gz && \
    mv boost_${BOOST_VERSION_UNDERSCORE} /usr/local/boost && \
    rm boost_${BOOST_VERSION_UNDERSCORE}.tar.gz

WORKDIR /usr/local/boost
RUN ./bootstrap.sh --prefix=/usr/boost && \
    ./b2 install --with-system --with-thread --with-serialization --with-regex --with-iostreams --with-program_options -j$(nproc) && \
    ldconfig

# Stage 2: Build RDKit
FROM rockylinux:${ROCKY_VERSION} AS builder
ARG RDKIT_GIT_REF=Release_2024_03_1
ARG POSTGRES_VERSION=16

# Copy built Boost from boost-builder stage
COPY --from=boost-builder /usr/boost /usr/boost
COPY --from=boost-builder /usr/lib/libboost_* /usr/lib/

# Build dependencies (excluding boost-devel since we built it ourselves)
RUN dnf install -y epel-release && \
    dnf config-manager --set-enabled crb && \
    dnf install -y \
    gcc-c++ \
    make \
    cmake \
    git \
    wget \
    tar \
    eigen3-devel \
    freetype-devel \
    zlib-devel \
    xz-devel \
    diffutils \
    && dnf clean all

# Update library cache to include custom Boost
RUN ldconfig

# Postgres repositories and devel headers
RUN set -euo pipefail; \
    POSTGRES_MAJOR_VERSION=$(echo ${POSTGRES_VERSION} | cut -d. -f1); \
    PG_ARCH=$(uname -m); \
    case "${PG_ARCH}" in \
    x86_64) PG_ARCH='x86_64' ;; \
    aarch64) PG_ARCH='aarch64' ;; \
    *) echo "Unsupported architecture: ${PG_ARCH}" && exit 1 ;; \
    esac; \
    dnf install -y https://download.postgresql.org/pub/repos/yum/reporpms/EL-9-${PG_ARCH}/pgdg-redhat-repo-latest.noarch.rpm && \
    dnf -qy module disable postgresql && \
    dnf install -y postgresql${POSTGRES_MAJOR_VERSION}-devel

WORKDIR /opt
RUN git clone https://github.com/rdkit/rdkit.git
WORKDIR /opt/rdkit
RUN git checkout ${RDKIT_GIT_REF}

RUN mkdir build
WORKDIR /opt/rdkit/build

# Set path for pg_config so cmake finds it - unnecessary with full paths below
# ENV PATH=$PATH:/usr/pgsql-${POSTGRES_VERSION}/bin

RUN POSTGRES_MAJOR_VERSION=$(echo ${POSTGRES_VERSION} | cut -d. -f1) && \
    PG_CONFIG=/usr/pgsql-${POSTGRES_MAJOR_VERSION}/bin/pg_config && \
    mkdir -p /usr/pgsql-${POSTGRES_MAJOR_VERSION}/lib && \
    mkdir -p /usr/pgsql-${POSTGRES_MAJOR_VERSION}/share/extension && \
    cmake .. \
    -Wno-dev \
    -D RDK_BUILD_CAIRO_SUPPORT=OFF \
    -D RDK_BUILD_INCHI_SUPPORT=ON \
    -D RDK_BUILD_AVALON_SUPPORT=ON \
    -D RDK_BUILD_PYTHON_WRAPPERS=OFF \
    -D RDK_BUILD_DESCRIPTORS3D=ON \
    -D RDK_BUILD_FREESASA_SUPPORT=OFF \
    -D RDK_BUILD_COORDGEN_SUPPORT=ON \
    -D RDK_BUILD_MOLINTERCHANGE_SUPPORT=OFF \
    -D RDK_BUILD_YAEHMOP_SUPPORT=OFF \
    -D RDK_BUILD_STRUCTCHECKER_SUPPORT=OFF \
    -D RDK_USE_URF=OFF \
    -D RDK_BUILD_PGSQL=ON \
    -D RDK_PGSQL_STATIC=ON \
    -D PostgreSQL_CONFIG=$PG_CONFIG \
    -D PostgreSQL_INCLUDE_DIR=$($PG_CONFIG --includedir) \
    -D PostgreSQL_TYPE_INCLUDE_DIR=$($PG_CONFIG --includedir-server) \
    -D PostgreSQL_LIBRARY_DIR=$($PG_CONFIG --libdir) \
    -D PostgreSQL_LIBRARY=$($PG_CONFIG --libdir)/libpq.so \
    -D RDK_INSTALL_INTREE=OFF \
    -D CMAKE_INSTALL_PREFIX=/usr \
    -D CMAKE_BUILD_TYPE=Release
RUN make -j$(nproc)

# Install the extension
WORKDIR /opt/rdkit/build/Code/PgSQL/rdkit
RUN make install

# Stage artifacts to a fixed path to handle version differences in COPY
RUN POSTGRES_MAJOR_VERSION=$(echo ${POSTGRES_VERSION} | cut -d. -f1) && \
    mkdir -p /opt/artifacts/lib /opt/artifacts/extension && \
    ls /usr/pgsql-${POSTGRES_MAJOR_VERSION} && \
    ls /usr/pgsql-${POSTGRES_MAJOR_VERSION}/share/extension/ && \
    cp /usr/pgsql-${POSTGRES_MAJOR_VERSION}/lib/rdkit.so /opt/artifacts/lib/ && \
    cp /usr/pgsql-${POSTGRES_MAJOR_VERSION}/share/extension/*rdkit* /opt/artifacts/extension/


# Stage 3: Final Image
FROM rockylinux:${ROCKY_VERSION}
ARG POSTGRES_VERSION
ARG POSTGRES_MAJOR_VERSION
ARG RDKIT_GIT_REF

LABEL org.opencontainers.image.title="RDKit PostgreSQL" \
    org.opencontainers.image.description="PostgreSQL image with RDKit extension pre-installed" \
    org.opencontainers.image.vendor="Cheminfo" \
    org.opencontainers.image.version="${RDKIT_GIT_REF}" \
    org.opencontainers.image.licenses="BSD-3-Clause"

# Copy built Boost from boost-builder stage
COPY --from=boost-builder /usr/boost /usr/boost
COPY --from=boost-builder /usr/lib/libboost_* /usr/lib/
RUN ldconfig

# Install Runtime dependencies and PostgreSQL
RUN set -eux; \
    POSTGRES_MAJOR_VERSION=$(echo ${POSTGRES_VERSION} | cut -d. -f1); \
    dnf install -y epel-release; \
    dnf config-manager --set-enabled crb; \
    dnf install -y https://download.postgresql.org/pub/repos/yum/reporpms/EL-9-$(uname -m)/pgdg-redhat-repo-latest.noarch.rpm; \
    dnf -qy module disable postgresql; \
    dnf install -y \
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

# Copy artifacts from builder
COPY --from=builder /opt/artifacts/lib/rdkit.so /tmp/rdkit.so
COPY --from=builder /opt/artifacts/extension/ /tmp/extension/

RUN POSTGRES_MAJOR_VERSION=$(echo ${POSTGRES_VERSION} | cut -d. -f1) && \
    mkdir -p /usr/pgsql-${POSTGRES_MAJOR_VERSION}/lib && \
    mkdir -p /usr/pgsql-${POSTGRES_MAJOR_VERSION}/share/extension && \
    cp /tmp/rdkit.so /usr/pgsql-${POSTGRES_MAJOR_VERSION}/lib/ && \
    cp /tmp/extension/* /usr/pgsql-${POSTGRES_MAJOR_VERSION}/share/extension/ && \
    rm -rf /tmp/rdkit.so /tmp/extension

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