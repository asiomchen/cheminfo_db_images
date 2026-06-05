# Cheminformatics PostgreSQL Images

[![RDKit Dist GHCR](https://img.shields.io/badge/GHCR-rdkit--postgres--dist-2496ED?logo=github&logoColor=fff)](https://github.com/asiomchen/cheminfo_db_images/pkgs/container/rdkit-postgres-dist)
[![RDKit GHCR](https://img.shields.io/badge/GHCR-rdkit--postgres-2496ED?logo=github&logoColor=fff)](https://github.com/asiomchen/cheminfo_db_images/pkgs/container/rdkit-postgres)
[![Bingo Dist GHCR](https://img.shields.io/badge/GHCR-bingo--dist-2496ED?logo=github&logoColor=fff)](https://github.com/asiomchen/cheminfo_db_images/pkgs/container/bingo-dist)
[![Bingo GHCR](https://img.shields.io/badge/GHCR-bingo--postgres-2496ED?logo=github&logoColor=fff)](https://github.com/asiomchen/cheminfo_db_images/pkgs/container/bingo-postgres)

Docker images for PostgreSQL with cheminformatics extensions, built on Rocky Linux 9 and published for `linux/amd64` and `linux/arm64`.

This repository publishes four GHCR packages:

| Package | Purpose |
| :--- | :--- |
| `ghcr.io/asiomchen/rdkit-postgres-dist` | RDKit PostgreSQL extension artifact image. |
| `ghcr.io/asiomchen/rdkit-postgres` | Ready-to-run PostgreSQL image with RDKit installed. |
| `ghcr.io/asiomchen/bingo-dist` | Bingo PostgreSQL extension artifact image. |
| `ghcr.io/asiomchen/bingo-postgres` | Ready-to-run PostgreSQL image with Bingo installed. |

## Tag Naming

Distribution artifact images are tagged by extension version and PostgreSQL major:

```text
<extension-version>-postgres<postgres-major>
```

Examples:

```text
ghcr.io/asiomchen/rdkit-postgres-dist:2025.09.5-postgres17
ghcr.io/asiomchen/bingo-dist:1.43.0-postgres17
```

Final runtime images are tagged by Rocky Linux version, PostgreSQL version, extension name, and extension version:

```text
rocky<rocky-major>-postgres<postgres-minor>-<extension><extension-version>
rocky<rocky-major>-postgres<postgres-major>-<extension><extension-version>
postgres<postgres-major>-<extension><extension-version>
postgres<postgres-minor>-<extension><extension-version>
```

Examples:

```text
ghcr.io/asiomchen/rdkit-postgres:rocky9-postgres17.10-rdkit2025.09.5
ghcr.io/asiomchen/rdkit-postgres:postgres17-rdkit2025.09.5
ghcr.io/asiomchen/bingo-postgres:rocky9-postgres17.10-bingo1.43.0
ghcr.io/asiomchen/bingo-postgres:postgres17-bingo1.43.0
```

Tags without the `rocky9-` prefix are Rocky Linux 9 aliases. Major-only PostgreSQL tags, such as `postgres17-rdkit2025.09.5`, point at the latest PostgreSQL minor version built for that major.

## RDKit Dist

`ghcr.io/asiomchen/rdkit-postgres-dist` is a small artifact image containing a packaged RDKit PostgreSQL cartridge for one RDKit version and one PostgreSQL major version. It is intended for building final runtime images, not for running PostgreSQL directly.

The image contains:

```text
/out/rdkit-postgres.tgz
/out/rdkit-postgres<postgres-major>-linux-<arch>-rdkit<rdkit-version>.tgz
```

Use it to inspect or extract the packaged extension:

```bash
docker run --rm ghcr.io/asiomchen/rdkit-postgres-dist:2025.09.5-postgres17

container_id="$(docker create ghcr.io/asiomchen/rdkit-postgres-dist:2025.09.5-postgres17)"
docker cp "${container_id}:/out/rdkit-postgres.tgz" ./rdkit-postgres.tgz
docker rm "${container_id}"
tar -tzf ./rdkit-postgres.tgz
```

The final `rdkit-postgres` image consumes this package through the `RDKIT_DIST_IMAGE` Docker build argument.

## RDKit Postgres

`ghcr.io/asiomchen/rdkit-postgres` is a ready-to-run PostgreSQL image with RDKit installed, preloaded, and automatically created in fresh databases via `/docker-entrypoint-initdb.d/rdkit.sql`.

Run a PostgreSQL instance with RDKit:

```bash
docker run -d \
  --name rdkit-postgres \
  -e POSTGRES_PASSWORD=mysecretpassword \
  -e POSTGRES_DB=chemistry \
  -p 5432:5432 \
  -v rdkit_pgdata:/var/lib/postgresql/data \
  ghcr.io/asiomchen/rdkit-postgres:postgres17-rdkit2025.09.5
```

Check the extension:

```bash
docker exec rdkit-postgres \
  psql -U postgres -d chemistry -c "SELECT rdkit_version(); SELECT mol_logp(mol_from_smiles('CCO'));"
```

## Bingo Dist

`ghcr.io/asiomchen/bingo-dist` is a small artifact image containing a packaged Bingo PostgreSQL extension for one Bingo version and one PostgreSQL major version. It is intended for building final runtime images, not for running PostgreSQL directly.

The image contains:

```text
/out/bingo-postgres.tgz
/out/bingo-postgres<postgres-major>-linux-<arch>.tgz
```

Use it to inspect or extract the packaged extension:

```bash
docker run --rm ghcr.io/asiomchen/bingo-dist:1.43.0-postgres17

container_id="$(docker create ghcr.io/asiomchen/bingo-dist:1.43.0-postgres17)"
docker cp "${container_id}:/out/bingo-postgres.tgz" ./bingo-postgres.tgz
docker rm "${container_id}"
tar -tzf ./bingo-postgres.tgz
```

The final `bingo-postgres` image consumes this package through the `BINGO_DIST_IMAGE` Docker build argument.

## Bingo Postgres

`ghcr.io/asiomchen/bingo-postgres` is a ready-to-run PostgreSQL image with Bingo installed and initialized for fresh databases through `bingo_install.sql`.

Run a PostgreSQL instance with Bingo:

```bash
docker run -d \
  --name bingo-postgres \
  -e POSTGRES_PASSWORD=mysecretpassword \
  -e POSTGRES_DB=chemistry \
  -p 5432:5432 \
  -v bingo_pgdata:/var/lib/postgresql/data \
  ghcr.io/asiomchen/bingo-postgres:postgres17-bingo1.43.0
```

Check the extension:

```bash
docker exec bingo-postgres \
  psql -U postgres -d chemistry -c "SELECT bingo.GetVersion();"
```

## Common Runtime Configuration

The final PostgreSQL images use the standard PostgreSQL Docker environment variables:

| Variable | Description |
| :--- | :--- |
| `POSTGRES_PASSWORD` | Required password for the PostgreSQL superuser. |
| `POSTGRES_USER` | Optional user name, defaults to `postgres`. |
| `POSTGRES_DB` | Optional database name, defaults to the user name. |

Both final images include a `pg_isready` health check and use an entrypoint derived from the official PostgreSQL container image.

## Supported Software

| Component | Versions |
| :--- | :--- |
| **PostgreSQL (RDKit)** | 16, 17, 18 |
| **PostgreSQL (Bingo)** | 15, 16, 17 |
| **RDKit** | 2024.03.6, 2024.09.1, 2024.09.2, 2024.09.3, 2024.09.4, 2024.09.5, 2024.09.6, 2025.03.1, 2025.03.2, 2025.03.3, 2025.03.4, 2025.03.5, 2025.03.6, 2025.09.1, 2025.09.2, 2025.09.3, 2025.09.4, 2025.09.5, 2025.09.6, 2026.03.1, 2026.03.2, **2026.03.3 (latest)** |
| **Bingo** | 1.34.0, 1.35.0, 1.36.0, 1.37.0, 1.38.0, 1.39.0, 1.40.0, 1.41.0, 1.42.0, **1.43.0 (latest)** |
