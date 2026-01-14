# Docker Hub Tags Summary

This repository provides Docker images for PostgreSQL with cheminformatics extensions (RDKit and Bingo).


## Tag Naming Convention

### Universal Tags

Tags follow this pattern:

```
rocky{ROCKY_VERSION}-postgres{POSTGRES_VERSION}-{EXTENSION}{EXTENSION_VERSION}
```

Where:
- `ROCKY_VERSION`: Rocky Linux major version (currently 9)
- `POSTGRES_VERSION`: Full PostgreSQL version (e.g., 15.15, 16.11, 17.7)
- `EXTENSION`: `rdkit` or `bingo`
- `EXTENSION_VERSION`: Extension version (e.g., `2024.03.6` for RDKit, `1.36.0` for Bingo)

### Alternative Tags (Rocky Linux 9)

For Rocky Linux 9, simplified tags without the OS prefix are available:

```
postgres{POSTGRES_VERSION}-{EXTENSION}{EXTENSION_VERSION}
```

For the **latest minor** PostgreSQL version, tags can use just the major version:

```
postgres{POSTGRES_MAJOR}-{EXTENSION}{EXTENSION_VERSION}
```

Example: `postgres17-rdkit2024.03.6` is equivalent to `rocky9-postgres17.7-rdkit2024.03.6` (assuming 17.7 is the latest minor version).

## Configuration

Image uses entrypoint script derived from official PostgreSQL image.

### Common Configuration

All images are configured with:
- PostgreSQL listening on all interfaces (`listen_addresses = '*'`)
- Shared preload libraries including the respective cheminformatics extension
- Health check using `pg_isready`
- Volume mounted at `/var/lib/postgresql/data`

### RDKit Specific Configuration

- RDKit extension is automatically created during database initialization
- RDKit is added to `shared_preload_libraries`

### Bingo Specific Configuration

- Bingo extension files are installed and configured
- Uses the official Bingo PostgreSQL extension

## Usage Examples

### RDKit
```bash
docker run -d \
  --name cheminfo-rdkit \
  -e POSTGRES_PASSWORD=secretpassword \
  -e POSTGRES_DB=chemistry \
  -p 5432:5432 \
  -v pgdata:/var/lib/postgresql/17/data \
  antonsiomchen/cheminfo-db:postgres17-rdkit2024.03.6
```

### Bingo
```bash
docker run -d \
  --name cheminfo-bingo \
  -e POSTGRES_PASSWORD=secretpassword \
  -e POSTGRES_DB=chemistry \
  -p 5432:5432 \
  -v pgdata:/var/lib/postgresql/17/data \
  antonsiomchen/cheminfo-db:postgres17-bingo1.36.0
```

## Supported Versions

### PostgreSQL Versions
- 15.x, 16.x, 17.x, 18.x (latest minor versions are used)

### RDKit Versions
- 2024.03.6, 2024.09.4, 2025.03.6, 2025.09.4

### Bingo Versions
- 1.34.0, 1.35.0, 1.36.0

### Rocky Linux Versions
- 9