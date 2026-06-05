#!/usr/bin/env bash
set -euo pipefail

# Configuration
REGISTRY="ghcr.io"
IMAGE_OWNER="asiomchen"
IMAGE_NAME="bingo-postgres"

# Version matrices
ROCKY_VERSIONS=("9")
POSTGRES_VERSIONS=("15" "16" "17")
BINGO_VERSIONS=("1.34.0" "1.35.0" "1.36.0")

get_latest_pg_minor() {
    local major_ver=$1
    python3 ../scripts/registry_helpers.py latest-pg-minor "$major_ver"
}

build_cmd() {
    local rocky_version=$1
    local postgres_minor_version=$2
    local bingo_version=$3
    
    local build_tag="rocky${rocky_version}-postgres${postgres_minor_version}-bingo${bingo_version}"    
    echo "echo Building image: ${build_tag}"
    
    local postgres_major_version=$(echo ${postgres_minor_version} | cut -d. -f1)

    # Build the image
    echo "docker build --platform linux/amd64 \\
        --build-arg ROCKY_VERSION=${rocky_version} \\
        --build-arg POSTGRES_VERSION=${postgres_minor_version} \\
        --build-arg POSTGRES_MAJOR_VERSION=${postgres_major_version} \\
        --build-arg BINGO_VERSION=${bingo_version} \\
        -t ${REGISTRY}/${IMAGE_OWNER}/${IMAGE_NAME}:${build_tag} \\
        -f Dockerfile \\
        . 2>&1 | tee build-${build_tag}.log"
    echo "" 
}

test_image() {
    local image_tag=$1
    # start image wait 10 seconds
    echo "docker run -d -p 5432:5432 --name test-${image_tag} -e POSTGRES_PASSWORD=postgres ${REGISTRY}/${IMAGE_OWNER}/${IMAGE_NAME}:${image_tag} "
    echo "sleep 5"
    # Create extension and check version
    echo "docker exec test-${image_tag} psql -U postgres -c 'SELECT bingo.GetVersion();'"
    echo "PGPASSWORD=postgres psql -U postgres -p 5432 -h localhost -c 'SELECT bingo.GetVersion();'"
    echo "docker stop test-${image_tag}"
    echo "docker rm test-${image_tag}"  
    echo ""
}

push_cmd() {
    local rocky_version=$1
    local postgres_version=$2
    local bingo_version=$3
    local build_tag="rocky${rocky_version}-postgres${postgres_version}-bingo${bingo_version}"
    
    echo "echo Pushing image: ${build_tag}"
    
    # Push the image
    echo "docker push ${REGISTRY}/${IMAGE_OWNER}/${IMAGE_NAME}:${build_tag}"
}

echo "set -euo pipefail"
counter=0
for rocky_version in "${ROCKY_VERSIONS[@]}"; do
    for postgres_version in "${POSTGRES_VERSIONS[@]}"; do
        for bingo_version in "${BINGO_VERSIONS[@]}"; do
            LATEST_MINOR=$(get_latest_pg_minor $postgres_version)
            build_cmd "$rocky_version" "$LATEST_MINOR" "$bingo_version"
            build_tag="rocky${rocky_version}-postgres${LATEST_MINOR}-bingo${bingo_version}" 
            
            test_image "$build_tag"
            push_cmd "$rocky_version" "$LATEST_MINOR" "$bingo_version"
            
            # Check if this is the latest minor version
            postgres_major_version=$(echo ${postgres_version} | cut -d. -f1)
            
            echo "echo Tagging and pushing latest major version tag: ${postgres_major_version}"
            echo "docker tag ${REGISTRY}/${IMAGE_OWNER}/${IMAGE_NAME}:${build_tag} ${REGISTRY}/${IMAGE_OWNER}/${IMAGE_NAME}:rocky${rocky_version}-postgres${postgres_major_version}-bingo${bingo_version}"
            echo "docker push ${REGISTRY}/${IMAGE_OWNER}/${IMAGE_NAME}:rocky${rocky_version}-postgres${postgres_major_version}-bingo${bingo_version}"
            
            # if rocky == 9 omit rocky
            if [ "$rocky_version" == "9" ]; then
                REPO=${REGISTRY}/${IMAGE_OWNER}/${IMAGE_NAME}
                echo "docker tag ${REPO}:${build_tag} ${REPO}:postgres${postgres_major_version}-bingo${bingo_version}"
                echo "docker push ${REPO}:postgres${postgres_major_version}-bingo${bingo_version}"
                echo "docker tag ${REPO}:${build_tag} ${REPO}:postgres${LATEST_MINOR}-bingo${bingo_version}"
                echo "docker push ${REPO}:postgres${LATEST_MINOR}-bingo${bingo_version}"
            fi
            counter=$((counter+1))
            echo ""
        done
    done
done

echo "Total images: $counter" 1>&2
