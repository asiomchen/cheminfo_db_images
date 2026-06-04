# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This repository contains Docker image definitions for PostgreSQL with cheminformatics extensions (RDKit and Bingo) built on Rocky Linux 9. Images are published to GHCR as `ghcr.io/asiomchen/cheminfo-db`.

## Repository Structure

Two independent image families, each in their own directory:

- `rdkit/` — Multi-stage build: compiles Boost from source, builds RDKit from the GitHub source at a specific git ref, then assembles the final image. RDKit is added to `shared_preload_libraries` and the extension is auto-created in the default DB via `/docker-entrypoint-initdb.d/rdkit.sql`.
- `bingo/` — Two-stage build: downloads the Bingo pre-built binary from the EPAM lifecycle website (via `bingo-pg-install.sh`), then installs into the final image. Bingo is initialized via `bingo_install.sql` placed in `/docker-entrypoint-initdb.d/`.

Both directories share the same pattern:
- `Dockerfile` — the image definition
- `entrypoint.sh` — a copy of the official PostgreSQL Docker entrypoint script adapted for Rocky Linux (uses `gosu` for privilege dropping, processes `/docker-entrypoint-initdb.d/`)
- `build.sh` — a script that **generates** shell commands (outputs to stdout); run as `./build.sh > cmds.sh` to produce the actual build/test/push commands
- `cmds.sh` — the generated build/test/push commands (committed artifact, regenerate with `build.sh`)
- `compose.yaml` — Docker Compose file for local testing of a single image

## Key Workflows

### Regenerate build commands

```bash
cd rdkit && ./build.sh > cmds.sh
cd bingo && ./build.sh > cmds.sh
```

`build.sh` fetches the latest PostgreSQL minor version from PGDG repository metadata for each configured major version, then outputs shell commands to build, test, and push all version matrix combinations.

### Build a single image manually

```bash
# RDKit
docker build --platform linux/amd64 \
  --build-arg ROCKY_VERSION=9 \
  --build-arg POSTGRES_VERSION=17.7 \
  --build-arg POSTGRES_MAJOR_VERSION=17 \
  --build-arg RDKIT_GIT_REF=Release_2024_03_6 \
  -t ghcr.io/asiomchen/cheminfo-db:rocky9-postgres17.7-rdkit2024.03.6 \
  -f rdkit/Dockerfile rdkit/

# Bingo
docker build --platform linux/amd64 \
  --build-arg ROCKY_VERSION=9 \
  --build-arg POSTGRES_VERSION=17.7 \
  --build-arg POSTGRES_MAJOR_VERSION=17 \
  --build-arg BINGO_VERSION=1.36.0 \
  -t ghcr.io/asiomchen/cheminfo-db:rocky9-postgres17.7-bingo1.36.0 \
  -f bingo/Dockerfile bingo/
```

### Test a built image

```bash
# RDKit
docker run -d -p 5432:5432 --name test-rdkit -e POSTGRES_PASSWORD=postgres ghcr.io/asiomchen/cheminfo-db:<tag>
sleep 5
docker exec test-rdkit psql -U postgres -c "SELECT rdkit_version(); SELECT mol_logp(mol_from_smiles('CCO'));"
docker stop test-rdkit && docker rm test-rdkit

# Bingo
docker exec test-bingo psql -U postgres -c 'SELECT bingo.GetVersion();'
```

### Run with Docker Compose

```bash
cd rdkit && docker compose up   # or cd bingo && docker compose up
```

## Image Tagging Convention

Tags follow the pattern `rocky<OS>-postgres<MINOR>-<ext><VERSION>`. For Rocky Linux 9 (the only supported OS), simplified tags without the `rocky9-` prefix are also pushed. The `build.sh` scripts push three tag variants per combination: full (`rocky9-postgres17.7-rdkit...`), major-only (`postgres17-rdkit...`), and minor-specific without OS prefix (`postgres17.7-rdkit...`).

## RDKit Build Args

RDKit versions in `build.sh` use underscores (`2024_03_6`) which get converted to dots (`2024.03.6`) for tags, and are passed to Docker as `RDKIT_GIT_REF=Release_2024_03_6` to match the GitHub tag format.

## Version Matrices

- **RDKit** (`rdkit/build.sh`): PostgreSQL 16, 17, 18 × RDKit 2024.03.6, 2024.09.4, 2025.03.6, 2025.09.4
- **Bingo** (`bingo/build.sh`): PostgreSQL 15, 16, 17 × Bingo 1.34.0, 1.35.0, 1.36.0

To add a new version, update the relevant array in the appropriate `build.sh` and regenerate `cmds.sh`.
