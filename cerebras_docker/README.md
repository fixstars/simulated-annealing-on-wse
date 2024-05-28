# cerebras_docker

Docker image for cerebras

## Build

Please place the tar.gz of the Cerebras SDK in this directory under the name `Cerabras-SDK.tar.gz`.

```console
cd /path/to/cerebras_docker
# Double quotes are required.
wget "[Cerebras-SDK Download Full Path]" -O Cerebras-SDK.tar.gz
```

```console
cerebras_docker
├── Cerebras-SDK.tar.gz  <-- Here
├── Dockerfile
├── XXX.sh
└── README.md
```

Then, build the Docker image by `build.sh`

```console
./build.sh
```

This script is the same as the following commands.

```console
cd /path/to/cerebras_docker
docker build \
  --build-arg UID="$(id -u)" \
  --build-arg GID="$(id -g)" \
  --tag cerebras:${USER} .
```

## Launch

### run docker image

Please set `AMPLIFY_TOKEN` environment.

```console
./run_cerebras.sh
```

This script is the same as the following commands.

```console
cd /path/to/cerebras_docker
docker run \
       -it \
       --rm \
       --privileged \
       --name cerebras \
       --env AMPLIFY_TOKEN=$AMPLIFY_TOKEN \
       --env SA_WIDTH="$SA_WIDTH" \
       --env SA_HEIGHT="$SA_HEIGHT" \
       --mount "type=bind,source=$(realpath /path/to/cerebras_sa),target=/home/cerebras/cerebras_sa/" \
       cerebras:${USER}
```

### execute cerebras_sa in docker image

Please set `AMPLIFY_TOKEN` environment.

```console
./exec_cerebras_sa.sh
```

This script is the same as the following commands.

```console
cd /path/to/cerebras_docker
docker run \
       -it \
       --rm \
       --privileged \
       --name cerebras \
       --env AMPLIFY_TOKEN=$AMPLIFY_TOKEN \
       --env SA_WIDTH="$SA_WIDTH" \
       --env SA_HEIGHT="$SA_HEIGHT" \
       --mount "type=bind,source=$(realpath /path/to/cerebras_sa),target=/home/cerebras/cerebras_sa/" \
       cerebras:${USER} \
       /bin/bash -c \
         "export PATH=\$HOME/cs_sdk:\$PATH && \
          cd \$HOME/cerebras_sa/src && \
          ./commands.sh"
```

### run docker image without cerebras_sa (optional)

```console
cd /path/to/cerebras_docker
docker run -it --privileged --rm --name cerebras cerebras:${USER}
```
