#!/usr/bin/env bash
echo "set -euo pipefail"
set -euo pipefail

# Configuration
REGISTRY="ghcr.io"
IMAGE_OWNER="asiomchen"
IMAGE_NAME="rdkit-postgres"
DIST_IMAGE_NAME="rdkit-postgres-dist"

# Version matrices
ROCKY_VERSIONS=("9")
POSTGRES_VERSIONS=("16" "17" "18")
RDKIT_VERSIONS=("2024_03_6" "2024_09_4" "2025_09_4" "2025_09_5")

get_latest_pg_minor() {
    local major_ver=$1
    python3 ../scripts/registry_helpers.py latest-pg-minor "$major_ver"
}

dist_image_ref() {
    local postgres_major_version=$1
    local rdkit_version=$2

    local clean_rdkit_version=$(echo $rdkit_version | sed 's/Release_//g' | sed 's/_/./g')
    echo "${REGISTRY}/${IMAGE_OWNER}/${DIST_IMAGE_NAME}:${clean_rdkit_version}-postgres${postgres_major_version}"
}

build_dist_local_cmd() {
    local rocky_version=$1
    local postgres_major_version=$2
    local rdkit_version=$3

    local clean_rdkit_version=$(echo $rdkit_version | sed 's/Release_//g' | sed 's/_/./g')
    local dist_ref
    dist_ref=$(dist_image_ref "$postgres_major_version" "$rdkit_version")
    echo "echo Building RDKit dist amd64 for local test: ${dist_ref}"
    echo "docker buildx build --platform linux/amd64 \\"
    echo "    --build-arg ROCKY_VERSION=${rocky_version} \\"
    echo "    --build-arg POSTGRES_MAJOR_VERSION=${postgres_major_version} \\"
    echo "    --build-arg RDKIT_GIT_REF=Release_${rdkit_version} \\"
    echo "    --build-arg RDKIT_VERSION=${clean_rdkit_version} \\"
    echo "    -t ${dist_ref} \\"
    echo "    --load \\"
    echo "    -f Dockerfile.dist . 2>&1 | tee build-rdkit-dist-postgres${postgres_major_version}-rdkit${clean_rdkit_version}.log"
    echo ""
}

push_dist_multiarch_cmd() {
    local rocky_version=$1
    local postgres_major_version=$2
    local rdkit_version=$3

    local clean_rdkit_version=$(echo $rdkit_version | sed 's/Release_//g' | sed 's/_/./g')
    local dist_ref
    dist_ref=$(dist_image_ref "$postgres_major_version" "$rdkit_version")
    echo "echo Pushing RDKit dist multi-arch: ${dist_ref}"
    echo "docker buildx build --platform linux/amd64,linux/arm64 \\"
    echo "    --build-arg ROCKY_VERSION=${rocky_version} \\"
    echo "    --build-arg POSTGRES_MAJOR_VERSION=${postgres_major_version} \\"
    echo "    --build-arg RDKIT_GIT_REF=Release_${rdkit_version} \\"
    echo "    --build-arg RDKIT_VERSION=${clean_rdkit_version} \\"
    echo "    -t ${dist_ref} \\"
    echo "    --push \\"
    echo "    -f Dockerfile.dist . 2>&1 | tee build-rdkit-dist-postgres${postgres_major_version}-rdkit${clean_rdkit_version}.log"
    echo ""
}

# Build amd64 locally so the image is available for testing before the multiarch push.
build_local_cmd() {
    local rocky_version=$1
    local postgres_minor_version=$2
    local rdkit_version=$3

    local clean_rdkit_version=$(echo $rdkit_version | sed 's/Release_//g' | sed 's/_/./g')
    local postgres_major_version=$(echo ${postgres_minor_version} | cut -d. -f1)
    local build_tag="rocky${rocky_version}-postgres${postgres_minor_version}-rdkit${clean_rdkit_version}"
    local dist_ref
    dist_ref=$(dist_image_ref "$postgres_major_version" "$rdkit_version")
    echo "echo Building amd64 for local test: ${build_tag}"
    echo "docker buildx build --platform linux/amd64 \\"
    echo "    --build-arg ROCKY_VERSION=${rocky_version} \\"
    echo "    --build-arg POSTGRES_VERSION=${postgres_minor_version} \\"
    echo "    --build-arg POSTGRES_MAJOR_VERSION=${postgres_major_version} \\"
    echo "    --build-arg RDKIT_GIT_REF=Release_${rdkit_version} \\"
    echo "    --build-arg RDKIT_DIST_IMAGE=${dist_ref} \\"
    echo "    -t ${REGISTRY}/${IMAGE_OWNER}/${IMAGE_NAME}:${build_tag} \\"
    echo "    --load \\"
    echo "    -f Dockerfile . 2>&1 | tee build-${build_tag}.log"
    echo ""
}

test_image() {
    local image_tag=$1
    echo "docker run -d -p 5432:5432 --name test-${image_tag} -e POSTGRES_PASSWORD=postgres ${REGISTRY}/${IMAGE_OWNER}/${IMAGE_NAME}:${image_tag}"
    echo "sleep 5"
    echo "docker exec test-${image_tag} psql -U postgres -c \"SELECT rdkit_version();SELECT mol_logp(mol_from_smiles('CCO'));\""
    echo "PGPASSWORD=postgres psql -U postgres -p 5432 -h localhost -c \"SELECT rdkit_version(); SELECT is_valid_smiles('CCO');\""
    echo "docker stop test-${image_tag}"
    echo "docker rm test-${image_tag}"
    echo ""
}

# Build both arches and push all tag variants in one shot.
# amd64 layers are already cached from build_local_cmd, so only arm64 needs to be built.
push_multiarch_cmd() {
    local rocky_version=$1
    local postgres_minor_version=$2
    local rdkit_version=$3

    local clean_rdkit_version=$(echo $rdkit_version | sed 's/Release_//g' | sed 's/_/./g')
    local postgres_major_version=$(echo ${postgres_minor_version} | cut -d. -f1)
    local build_tag="rocky${rocky_version}-postgres${postgres_minor_version}-rdkit${clean_rdkit_version}"
    local dist_ref
    dist_ref=$(dist_image_ref "$postgres_major_version" "$rdkit_version")

    local tag_args="-t ${REGISTRY}/${IMAGE_OWNER}/${IMAGE_NAME}:${build_tag}"
    tag_args+=" \\"$'\n'"    -t ${REGISTRY}/${IMAGE_OWNER}/${IMAGE_NAME}:rocky${rocky_version}-postgres${postgres_major_version}-rdkit${clean_rdkit_version}"
    if [ "$rocky_version" == "9" ]; then
        tag_args+=" \\"$'\n'"    -t ${REGISTRY}/${IMAGE_OWNER}/${IMAGE_NAME}:postgres${postgres_major_version}-rdkit${clean_rdkit_version}"
        tag_args+=" \\"$'\n'"    -t ${REGISTRY}/${IMAGE_OWNER}/${IMAGE_NAME}:postgres${postgres_minor_version}-rdkit${clean_rdkit_version}"
    fi

    echo "echo Pushing multi-arch: ${build_tag}"
    echo "docker buildx build --platform linux/amd64,linux/arm64 \\"
    echo "    --build-arg ROCKY_VERSION=${rocky_version} \\"
    echo "    --build-arg POSTGRES_VERSION=${postgres_minor_version} \\"
    echo "    --build-arg POSTGRES_MAJOR_VERSION=${postgres_major_version} \\"
    echo "    --build-arg RDKIT_GIT_REF=Release_${rdkit_version} \\"
    echo "    --build-arg RDKIT_DIST_IMAGE=${dist_ref} \\"
    echo "    ${tag_args} \\"
    echo "    --push \\"
    echo "    -f Dockerfile . 2>&1 | tee build-${build_tag}.log"
    echo ""
}

# Output QEMU and buildx builder setup at the top of cmds.sh.
# Docker Desktop already ships with QEMU emulation; binfmt --install all
# handles standalone Linux hosts. The default builder on Docker Desktop
# supports multi-arch natively, so no custom builder is needed.
echo ""
echo "# Enable QEMU emulation for cross-platform builds (no-op on Docker Desktop)"
echo "docker run --privileged --rm tonistiigi/binfmt --install all"
echo "docker buildx use default"
echo ""

for rocky_version in "${ROCKY_VERSIONS[@]}"; do
    for postgres_version in "${POSTGRES_VERSIONS[@]}"; do
        for rdkit_version in "${RDKIT_VERSIONS[@]}"; do
            LATEST_MINOR=$(get_latest_pg_minor $postgres_version)
            clean_rdkit_version=$(echo $rdkit_version | sed 's/Release_//g' | sed 's/_/./g')
            postgres_major_version=$(echo ${LATEST_MINOR} | cut -d. -f1)
            build_tag="rocky${rocky_version}-postgres${LATEST_MINOR}-rdkit${clean_rdkit_version}"

            build_dist_local_cmd "$rocky_version" "$postgres_major_version" "$rdkit_version"
            build_local_cmd "$rocky_version" "$LATEST_MINOR" "$rdkit_version"
            test_image "$build_tag"
            push_dist_multiarch_cmd "$rocky_version" "$postgres_major_version" "$rdkit_version"
            push_multiarch_cmd "$rocky_version" "$LATEST_MINOR" "$rdkit_version"
        done
    done
done
