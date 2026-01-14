#!/usr/bin/env bash
echo "set -euo pipefail"
set -euo pipefail

# Configuration
DOCKER_USER="antonsiomchen"
IMAGE_NAME="cheminfo-db"

# Version matrices
ROCKY_VERSIONS=("9")
POSTGRES_VERSIONS=("16" "17" "18")
RDKIT_VERSIONS=("2024_03_6" "2024_09_4" "2025_03_6" "2025_09_4")

get_latest_pg_minor() {
    local major_ver=$1
    local output
    output=$(curl -s "https://registry.hub.docker.com/v2/repositories/library/postgres/tags/?page_size=100&name=${major_ver}.")
    
    echo "$output" | python3 -c "
import sys, json, re
try:
    data = json.load(sys.stdin)
    major_ver = sys.argv[1]
    tags = [r['name'] for r in data['results']]
    regex = re.compile(r'^' + re.escape(major_ver) + r'\.\d+$')
    valid_tags = [t for t in tags if regex.match(t)]
    valid_tags.sort(key=lambda s: [int(u) for u in s.split('.')])
    if valid_tags:
        print(valid_tags[-1])
except Exception:
    pass
" "$major_ver"
}

build_cmd() {
    local rocky_version=$1
    local postgres_minor_version=$2
    local rdkit_version=$3
    
    # Clean version string for tag (replace Release_ with nothing, or keep it?)
    # Let's keep it simple for now, or maybe strip 'Release_' and replace '_' with '.'
    local clean_rdkit_version=$(echo $rdkit_version | sed 's/Release_//g' | sed 's/_/./g')
    local postgres_major_version=$(echo ${postgres_minor_version} | cut -d. -f1)
    local build_tag="rocky${rocky_version}-postgres${postgres_minor_version}-rdkit${clean_rdkit_version}"    
    echo "echo Building image: ${build_tag}"
    
    # Build the image

    echo "docker build --platform linux/amd64  \\
        --build-arg ROCKY_VERSION=${rocky_version} \\
        --build-arg POSTGRES_VERSION=${postgres_minor_version} \\
        --build-arg POSTGRES_MAJOR_VERSION=${postgres_major_version} \\
        --build-arg RDKIT_GIT_REF=Release_${rdkit_version} \\
        -t ${DOCKER_USER}/${IMAGE_NAME}:${build_tag} \\
        -f Dockerfile \\
        . 2>&1 | tee build-${build_tag}.log"
    echo "" 
}

test_image() {
    local image_tag=$1
    # start image wait 10 seconds
    echo "docker run -d -p 5432:5432 --name test-${image_tag} -e POSTGRES_PASSWORD=postgres ${DOCKER_USER}/${IMAGE_NAME}:${image_tag} "
    echo "sleep 5"
    # Create extension and check version
    echo "docker exec test-${image_tag} psql -U postgres -c \"SELECT rdkit_version();SELECT mol_logp(mol_from_smiles('CCO'));\""
    echo "PGPASSWORD=postgres psql -U postgres -p 5432 -h localhost -c \"SELECT rdkit_version(); SELECT is_valid_smiles('CCO');\""
    echo "docker stop test-${image_tag}"
    echo "docker rm test-${image_tag}"  
    echo ""
}

push_cmd() {
    local rocky_version=$1
    local postgres_version=$2
    local rdkit_version=$3
    local clean_rdkit_version=$(echo $rdkit_version | sed 's/Release_//g' | sed 's/_/./g')
    local build_tag="rocky${rocky_version}-postgres${postgres_version}-rdkit${clean_rdkit_version}"
    
    echo "echo Pushing image: ${build_tag}"
    
    # Push the image
    echo "docker push ${DOCKER_USER}/${IMAGE_NAME}:${build_tag}"
}


for rocky_version in "${ROCKY_VERSIONS[@]}"; do
    for postgres_version in "${POSTGRES_VERSIONS[@]}"; do
        for rdkit_version in "${RDKIT_VERSIONS[@]}"; do
            LATEST_MINOR=$(get_latest_pg_minor $postgres_version)
            build_cmd "$rocky_version" "$LATEST_MINOR" "$rdkit_version"
            clean_rdkit_version=$(echo $rdkit_version | sed 's/Release_//g' | sed 's/_/./g')
            build_tag="rocky${rocky_version}-postgres${LATEST_MINOR}-rdkit${clean_rdkit_version}" 
            
            test_image "$build_tag"
            push_cmd "$rocky_version" "$LATEST_MINOR" "$rdkit_version"
            
            # Check if this is the latest minor version
            postgres_major_version=$(echo ${postgres_version} | cut -d. -f1)
            latest_minor=$(get_latest_pg_minor "$postgres_major_version")
            # write to stderr
            echo "echo Tagging and pushing latest major version tag: ${postgres_major_version}"
            echo "docker tag ${DOCKER_USER}/${IMAGE_NAME}:${build_tag} ${DOCKER_USER}/${IMAGE_NAME}:postgres${postgres_major_version}-rdkit${clean_rdkit_version}"
            echo "docker push ${DOCKER_USER}/${IMAGE_NAME}:postgres${postgres_major_version}-rdkit${clean_rdkit_version}"
            # if rocky == 9 omit rocky
            if [ "$rocky_version" == "9" ]; then
                REPO=${DOCKER_USER}/${IMAGE_NAME}
                echo "docker tag ${REPO}:${build_tag} ${REPO}:postgres${postgres_major_version}-rdkit${clean_rdkit_version}"
                echo "docker push ${REPO}:postgres${postgres_major_version}-rdkit${clean_rdkit_version}"
                echo "docker tag ${REPO}:${build_tag} ${REPO}:postgres${latest_minor}-rdkit${clean_rdkit_version}"
                echo "docker push ${REPO}:postgres${latest_minor}-rdkit${clean_rdkit_version}"
            fi

            echo ""
        done
    done
done
