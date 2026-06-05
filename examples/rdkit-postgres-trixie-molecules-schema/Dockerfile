FROM ghcr.io/asiomchen/rdkit-postgres-dist:2025.09.5-postgres17 AS rdkit_dist

FROM postgres:17-trixie

COPY --from=rdkit_dist /out/rdkit-postgres.tgz /tmp/rdkit-postgres.tgz

RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
      libbz2-1.0 \
      libfreetype6; \
    rm -rf /var/lib/apt/lists/*; \
    mkdir -p /tmp/rdkit-postgres /docker-entrypoint-initdb.d; \
    tar -xzf /tmp/rdkit-postgres.tgz -C /tmp/rdkit-postgres --strip-components=1; \
    cd /tmp/rdkit-postgres; \
    sh ./rdkit-pg-install.sh \
      -libdir "$(pg_config --pkglibdir)" \
      -sharedir "$(pg_config --sharedir)/extension" \
      -y; \
    sed -ri "s!^#?(shared_preload_libraries)[[:space:]]*=.*!\1 = 'rdkit'!" "$(pg_config --sharedir)/postgresql.conf.sample"; \
    printf '%s\n' \
      "CREATE SCHEMA IF NOT EXISTS molecules;" \
      "CREATE EXTENSION IF NOT EXISTS rdkit WITH SCHEMA molecules;" \
      "-- RDKit SQL wrapper functions may call other RDKit functions without schema qualification." \
      "-- Put the extension schema on the database search path for normal sessions." \
      "DO \$\$ BEGIN EXECUTE format('ALTER DATABASE %I SET search_path = molecules, public', current_database()); END \$\$;" \
      > /docker-entrypoint-initdb.d/rdkit.sql; \
    rm -rf /tmp/rdkit-postgres /tmp/rdkit-postgres.tgz
