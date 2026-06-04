#!/usr/bin/env bash
set -euo pipefail

REGISTRY="ghcr.io"
IMAGE_OWNER="asiomchen"
IMAGE_NAME="cheminfo-db"
ROCKY_VERSION="9"
POSTGRES_MAJOR_VERSION="15"
POSTGRES_VERSION=""
BINGO_VERSION="1.43.0"
BINGO_DIST_IMAGE="${REGISTRY}/${IMAGE_OWNER}/bingo-dist:1.43.0-postgres15"
ARCHES=("amd64" "arm64")

usage() {
    cat <<'EOF'
Usage: ./test-final-local.sh [options]

Builds and smoke-tests the final Bingo PostgreSQL image locally for amd64 and arm64
using the source-built Bingo dist image as the loader stage input.

Options:
  --dist-image IMAGE       Override the Bingo dist image
  --arch ARCH              Limit testing to one architecture: amd64 or arm64
  --pg-version VERSION     Override the PostgreSQL minor version instead of auto-detecting latest PG15
  --help                   Show this help
EOF
}

get_latest_pg_minor() {
    local major_ver=$1
    python3 ../scripts/registry_helpers.py latest-pg-minor "$major_ver"
}

cleanup_container() {
    local container_name=$1
    docker rm -f "$container_name" >/dev/null 2>&1 || true
}

wait_for_postgres() {
    local container_name=$1
    local timeout_seconds=${2:-60}

    echo "Waiting for PostgreSQL in ${container_name}..."
    for i in $(seq 1 "$timeout_seconds"); do
        if docker exec "$container_name" pg_isready -U postgres >/dev/null 2>&1; then
            echo "PostgreSQL is ready after ${i}s"
            return 0
        fi
        sleep 1
    done

    echo "Timed out waiting for PostgreSQL in ${container_name}" >&2
    docker logs "$container_name" 2>&1 || true
    return 1
}

wait_for_bingo() {
    local container_name=$1
    local expected_version=$2
    local timeout_seconds=${3:-60}
    local version_output=""

    echo "Waiting for Bingo schema in ${container_name}..."
    for i in $(seq 1 "$timeout_seconds"); do
        version_output=$(docker exec "$container_name" psql -U postgres -Atqc "SELECT bingo.GetVersion();" 2>/dev/null || true)
        if [[ "${version_output}" == "${expected_version}" ]]; then
            echo "Bingo is ready after ${i}s"
            printf '%s\n' "${version_output}"
            return 0
        fi
        sleep 1
    done

    echo "Timed out waiting for Bingo schema in ${container_name}" >&2
    docker logs "$container_name" 2>&1 || true
    return 1
}

build_image() {
    local arch=$1
    local local_tag=$2

    echo "Building final image for linux/${arch}: ${local_tag}"
    docker buildx build \
        --platform "linux/${arch}" \
        --build-arg ROCKY_VERSION="${ROCKY_VERSION}" \
        --build-arg POSTGRES_VERSION="${POSTGRES_VERSION}" \
        --build-arg POSTGRES_MAJOR_VERSION="${POSTGRES_MAJOR_VERSION}" \
        --build-arg BINGO_VERSION="${BINGO_VERSION}" \
        --build-arg BINGO_DIST_IMAGE="${BINGO_DIST_IMAGE}" \
        -t "${local_tag}" \
        --load \
        -f Dockerfile \
        .
}

smoke_test_image() {
    local arch=$1
    local local_tag=$2
    local container_name=$3

    cleanup_container "$container_name"

    docker run -d \
        --platform "linux/${arch}" \
        --name "${container_name}" \
        -e POSTGRES_PASSWORD=postgres \
        "${local_tag}" >/dev/null

    if ! wait_for_postgres "$container_name" 60; then
        return 1
    fi

    local version_output
    if ! version_output=$(wait_for_bingo "$container_name" "${BINGO_VERSION}" 60); then
        return 1
    fi
    echo "Bingo version for ${arch}: ${version_output}"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dist-image)
            BINGO_DIST_IMAGE=$2
            shift 2
            ;;
        --arch)
            ARCHES=("$2")
            shift 2
            ;;
        --pg-version)
            POSTGRES_VERSION=$2
            shift 2
            ;;
        --help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown argument: $1" >&2
            usage
            exit 1
            ;;
    esac
done

for arch in "${ARCHES[@]}"; do
    case "${arch}" in
        amd64|arm64) ;;
        *)
            echo "Unsupported architecture: ${arch}" >&2
            exit 1
            ;;
    esac
done

if [[ -z "${POSTGRES_VERSION}" ]]; then
    POSTGRES_VERSION=$(get_latest_pg_minor "${POSTGRES_MAJOR_VERSION}")
fi

if [[ -z "${POSTGRES_VERSION}" ]]; then
    echo "Failed to detect latest PostgreSQL ${POSTGRES_MAJOR_VERSION} minor version" >&2
    exit 1
fi

echo "Using PostgreSQL ${POSTGRES_VERSION}"
echo "Using Bingo dist image ${BINGO_DIST_IMAGE}"
echo "Testing architectures: ${ARCHES[*]}"
echo "Using docker buildx builder: default"
echo "If linux/arm64 runtime fails on standalone Linux, enable emulation with:"
echo "  docker run --privileged --rm tonistiigi/binfmt --install all"

docker buildx use default

for arch in "${ARCHES[@]}"; do
    local_tag="${REGISTRY}/${IMAGE_OWNER}/${IMAGE_NAME}:local-postgres${POSTGRES_VERSION}-bingo${BINGO_VERSION}-${arch}"
    container_name="test-bingo-final-pg${POSTGRES_MAJOR_VERSION}-${arch}"

    trap 'cleanup_container "${container_name}"' EXIT

    build_image "${arch}" "${local_tag}"
    smoke_test_image "${arch}" "${local_tag}" "${container_name}"
    cleanup_container "${container_name}"
    trap - EXIT
done

echo "Local final-image smoke test passed for: ${ARCHES[*]}"
