# RDKit PostgreSQL Distribution Image

This repository builds RDKit PostgreSQL in two steps:

1. `rdkit-dist`: a small artifact image containing a reusable RDKit PostgreSQL cartridge archive.
2. `cheminfo-db`: the final PostgreSQL runtime image that installs the cartridge archive from `rdkit-dist`.

The purpose of the distribution image is to make the RDKit PostgreSQL cartridge easy to share and reuse without requiring every final image build to compile Boost and RDKit from source.

## Why This Exists

RDKit's PostgreSQL cartridge can be built in a way that depends on installed Boost and RDKit shared libraries. That makes the final runtime image more coupled to the build environment and harder to distribute as a standalone cartridge.

`rdkit/Dockerfile.dist` instead builds:

- Boost as static position-independent libraries.
- RDKit PostgreSQL with `RDK_PGSQL_STATIC=ON`.
- The PostgreSQL extension artifact `rdkit.so`.
- The extension control and SQL migration files.
- A small installer script for copying the files into a PostgreSQL installation.

The resulting `rdkit.so` is still a PostgreSQL shared object, but it does not require `libboost_*` or `libRDKit*` shared libraries at runtime.

## Image Names

Distribution image:

```text
antonsiomchen/rdkit-dist:<rdkit-version>-postgres<postgres-major>
```

Example:

```text
antonsiomchen/rdkit-dist:2025.09.5-postgres17
```

Final runtime image:

```text
antonsiomchen/cheminfo-db:rocky9-postgres<postgres-version>-rdkit<rdkit-version>
```

Example:

```text
antonsiomchen/cheminfo-db:rocky9-postgres17.10-rdkit2025.09.5
```

## What The Dist Image Contains

The dist image is an Alpine artifact image with `/out` as the important payload location.

Expected files:

```text
/out/rdkit-postgres.tgz
/out/rdkit-postgres<postgres-major>-linux-<arch>-rdkit<rdkit-version>.tgz
```

`rdkit-postgres.tgz` is a symlink to the versioned archive.

The archive layout is:

```text
rdkit-postgres17-linux-x86_64-rdkit2025.09.5/
  rdkit-pg-install.sh
  lib/
    rdkit.so
  share/
    extension/
      rdkit.control
      rdkit--*.sql
```

The installer expects explicit PostgreSQL destination directories:

```bash
sh ./rdkit-pg-install.sh \
  -libdir /usr/pgsql-17/lib \
  -sharedir /usr/pgsql-17/share/extension \
  -y
```

## Build The Dist Image

From the `rdkit` directory:

```bash
docker buildx build --platform linux/amd64 \
  --build-arg ROCKY_VERSION=9 \
  --build-arg POSTGRES_MAJOR_VERSION=17 \
  --build-arg RDKIT_GIT_REF=Release_2025_09_5 \
  --build-arg RDKIT_VERSION=2025.09.5 \
  -t antonsiomchen/rdkit-dist:2025.09.5-postgres17 \
  --load \
  -f Dockerfile.dist .
```

For a multi-architecture pushed image:

```bash
docker buildx build --platform linux/amd64,linux/arm64 \
  --build-arg ROCKY_VERSION=9 \
  --build-arg POSTGRES_MAJOR_VERSION=17 \
  --build-arg RDKIT_GIT_REF=Release_2025_09_5 \
  --build-arg RDKIT_VERSION=2025.09.5 \
  -t antonsiomchen/rdkit-dist:2025.09.5-postgres17 \
  --push \
  -f Dockerfile.dist .
```

## Inspect The Dist Image

List the packaged files:

```bash
docker run --rm antonsiomchen/rdkit-dist:2025.09.5-postgres17
```

Extract the archive locally:

```bash
container_id="$(docker create antonsiomchen/rdkit-dist:2025.09.5-postgres17)"
docker cp "${container_id}:/out/rdkit-postgres.tgz" ./rdkit-postgres.tgz
docker rm "${container_id}"
tar -tzf ./rdkit-postgres.tgz
```

Verify that the cartridge does not depend on Boost or RDKit shared libraries:

```bash
container_id="$(docker create antonsiomchen/rdkit-dist:2025.09.5-postgres17)"
docker cp "${container_id}:/out/rdkit-postgres.tgz" ./rdkit-postgres.tgz
docker rm "${container_id}"
mkdir -p /tmp/rdkit-postgres-dist
tar -xzf ./rdkit-postgres.tgz -C /tmp/rdkit-postgres-dist
ldd /tmp/rdkit-postgres-dist/rdkit-postgres*/lib/rdkit.so | grep -E 'libboost_|libRDKit' || true
```

The expected output from the last command is empty.

During the build, `Dockerfile.dist` also runs the same dependency check and fails the build if `ldd` reports `libboost_*` or `libRDKit`.

## Build The Final Runtime Image

The final `rdkit/Dockerfile` consumes the dist image with this build argument:

```text
RDKIT_DIST_IMAGE=antonsiomchen/rdkit-dist:2025.09.5-postgres17
```

Build example:

```bash
docker buildx build --platform linux/amd64 \
  --build-arg ROCKY_VERSION=9 \
  --build-arg POSTGRES_VERSION=17.10 \
  --build-arg POSTGRES_MAJOR_VERSION=17 \
  --build-arg RDKIT_GIT_REF=Release_2025_09_5 \
  --build-arg RDKIT_DIST_IMAGE=antonsiomchen/rdkit-dist:2025.09.5-postgres17 \
  -t antonsiomchen/cheminfo-db:rocky9-postgres17.10-rdkit2025.09.5 \
  --load \
  -f Dockerfile .
```

Inside the final image build:

1. The loader stage extracts `/out/rdkit-postgres.tgz`.
2. The runtime stage installs PostgreSQL server packages.
3. The runtime stage copies the extracted distribution to `/opt/rdkit-postgres`.
4. `rdkit-pg-install.sh` copies `rdkit.so` and extension SQL files into the PostgreSQL installation.
5. `/docker-entrypoint-initdb.d/rdkit.sql` creates the `rdkit` extension automatically for a fresh database.

## Verify The Final Runtime Image

Start a temporary database:

```bash
docker run -d \
  --name test-rdkit-postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_DB=postgres \
  -p 55432:5432 \
  antonsiomchen/cheminfo-db:rocky9-postgres17.10-rdkit2025.09.5
```

Wait for readiness:

```bash
docker exec test-rdkit-postgres pg_isready -U postgres
```

Run SQL checks:

```bash
docker exec test-rdkit-postgres \
  psql -U postgres -d postgres -v ON_ERROR_STOP=1 -Atc \
  "SELECT extname || ':' || extversion FROM pg_extension WHERE extname = 'rdkit';
   SELECT rdkit_version();
   SELECT mol_logp(mol_from_smiles('CCO'));
   SELECT is_valid_smiles('CCO');"
```

Expected output shape:

```text
rdkit:<extension-version>
<rdkit-version>
-0.0014
t
```

For the tested `2025.09.5` / PostgreSQL 17.10 build, the output was:

```text
rdkit:4.8.0
0.77.0
-0.0014
t
```

Verify the final image dependency state:

```bash
docker exec test-rdkit-postgres \
  sh -c "ldd /usr/pgsql-17/lib/rdkit.so | grep -E 'libboost_|libRDKit' || true"
```

Expected output is empty.

Clean up:

```bash
docker stop test-rdkit-postgres
docker rm test-rdkit-postgres
```

## Generated Build Commands

`rdkit/build.sh` generates commands for both images.

From the `rdkit` directory:

```bash
./build.sh > cmds.sh
```

For each Rocky/PostgreSQL/RDKit matrix item, the generated command order is:

1. Build local `rdkit-dist` for `linux/amd64`.
2. Build local final `cheminfo-db` image for `linux/amd64`.
3. Test the final image.
4. Push multi-architecture `rdkit-dist`.
5. Push multi-architecture final `cheminfo-db`.

The final image build receives the matching dist image through `RDKIT_DIST_IMAGE`.

## Runtime Dependencies

Because Boost and RDKit are statically linked into the PostgreSQL cartridge, the final image does not need Boost runtime packages or RDKit shared libraries.

The final image still needs the normal dynamic libraries reported by `ldd`, including PostgreSQL/libpq and system libraries. In the verified build, `rdkit.so` required libraries such as:

- `libpq.so.5`
- `libfreetype.so.6`
- `libbz2.so.1`
- `libz.so.1`
- `libstdc++.so.6`
- `libm.so.6`
- `libgcc_s.so.1`
- `libc.so.6`

These are provided by the PostgreSQL server package and the explicit runtime packages installed by the final image.

## Compatibility Notes

- The dist image is tied to a PostgreSQL major version because PostgreSQL extension binaries are built against PostgreSQL server headers and ABI expectations.
- Use a PostgreSQL 17 dist image only with PostgreSQL 17 final images.
- The dist image is architecture-specific internally. Multi-architecture tags publish separate archives for `linux/amd64` and `linux/arm64`.
- The dist image is intended as a build artifact, not as a runnable database image.
- A fresh database automatically creates the `rdkit` extension through `/docker-entrypoint-initdb.d/rdkit.sql`. Existing volumes are not reinitialized by PostgreSQL entrypoint logic, so create the extension manually if needed:

```sql
CREATE EXTENSION IF NOT EXISTS rdkit;
```
