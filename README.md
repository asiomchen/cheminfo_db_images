

# Cheminformatic Database Images

[![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=fff)](https://hub.docker.com/repository/docker/antonsiomchen/cheminfo-db)
![Docker Pulls](https://img.shields.io/docker/pulls/antonsiomchen/cheminfo-db?style=flat-square)
![Docker Stars](https://img.shields.io/docker/stars/antonsiomchen/cheminfo-db)


Yet another PostgreSQL images with pre-installed **RDKit** or **Bingo** extensions, built on **Rocky Linux 9**.


**Currently supports only Linux x86_64 architecture, arm64 support will be added later**

## Quick Start

Run a PostgreSQL instance with the RDKit extension:

```bash
docker run -d \
  --name cheminfo-db \
  -e POSTGRES_PASSWORD=mysecretpassword \
  -e POSTGRES_DB=chemistry \
  -p 5432:5432 \
  -v pgdata:/var/lib/postgresql/data \
  antonsiomchen/cheminfo-db:postgres17-rdkit2024.03.6
```

## Image Tagging

We provide flexible tagging to suit your needs:

| Format | Example |
| :--- | :--- |
| **Universal** | `rocky9-postgres17.7-rdkit2024.03.6` |
| **Simplified** | `postgres17-rdkit2024.03.6` (latest minor PG) |
| **Specific** | `postgres17.7-rdkit2024.03.6` |

*Note: Simplified tags without the `rocky9-` prefix default to Rocky Linux 9.*

## Supported Software

| Component | Versions |
| :--- | :--- |
| **PostgreSQL** | 15, 16, 17, 18 |
| **RDKit** | 2024.03.6, 2024.09.4, 2025.03.6, 2025.09.4 |
| **Bingo** | 1.34.0, 1.35.0, 1.36.0 |

## Key Features

- **Ready to Use**: Extensions are pre-installed and added to `shared_preload_libraries`.
- **Auto-Initialization**: RDKit extension is automatically created in the default database.
- **Official Entrypoint**: Uses the official PostgreSQL entrypoint script for full compatibility with standard environment variables (`POSTGRES_PASSWORD`, `POSTGRES_USER`, etc.).
- **Health Checks**: Built-in health check using `pg_isready`.

## Environment Variables

Supports all [standard PostgreSQL environment variables](https://hub.docker.com/_/postgres):

- `POSTGRES_PASSWORD`: (Required) Password for the superuser.
- `POSTGRES_USER`: (Optional) Default is `postgres`.
- `POSTGRES_DB`: (Optional) Default is the same as user.


## Building the Images

To build the images, run the following command:

```bash
./build.sh > cmds.sh
```

This generates a shell building images using latest minor versions of PostgreSQL and specified versions of RDKit and Bingo. 

**TODO: replace shell scrip for build tags with Python script with extended functionality**