# ChemInfo Database Docker Images

This repository contains Docker images for PostgreSQL with the Bingo chemistry extension, built on Rocky Linux.

## Image Naming Convention

Images are tagged using the format:
```
antonsiomchen/cheminfo-db:rocky<ROCKY_VERSION>-postgres<PG_MAJOR>-bingo<BINGO_VERSION>
```

For Rocky Linux 9, an alternative tag without the `rocky9-` prefix is also created:
```
antonsiomchen/cheminfo-db:postgres<PG_MAJOR>-bingo<BINGO_VERSION>
```

### Examples
- `antonsiomchen/cheminfo-db:rocky9-postgres17-bingo1.36.0`
- `antonsiomchen/cheminfo-db:postgres17-bingo1.36.0` (alternative for Rocky 9)


## Using the Images

This images install specified PostgreSQL version from the official PostgreSQL repository and use the [official PostgreSQL entrypoint script](https://hub.docker.com/_/postgres), so the usage is the same as for the official PostgreSQL image.

### Basic Usage

```bash
docker run -d \
  --name cheminfo-db \
  -e POSTGRES_PASSWORD=secretpassword \
  -e POSTGRES_DB=chemistry \
  -p 5432:5432 \
  -v pgdata:/var/lib/postgresql/17/docker \
  antonsiomchen/cheminfo-db:postgres17-bingo1.36.0
```

### Environment Variables

The image supports all standard PostgreSQL environment variables:

- `POSTGRES_PASSWORD` - Required. Password for the PostgreSQL superuser
- `POSTGRES_USER` - Optional. Default: `postgres`
- `POSTGRES_DB` - Optional. Default: same as `POSTGRES_USER`
- `POSTGRES_INITDB_ARGS` - Optional. Additional arguments for `initdb`
- `POSTGRES_HOST_AUTH_METHOD` - Optional. Default: `scram-sha-256` or `md5` (version dependent)
