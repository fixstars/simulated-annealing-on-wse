FROM ubuntu:22.04

ARG UID=1000
ARG GID=1000

## Change mirror
RUN sed -i.bak -e "s%mirror://[^ ]\+%http://ftp.jaist.ac.jp/pub/Linux/ubuntu/%g" /etc/apt/sources.list

# add new sudo user
ENV USER=cerebras
ENV HOME=/home/$USER
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -yq \
        wget curl git build-essential vim sudo lsb-release locales bash-completion tzdata gosu \
        autoconf automake cryptsetup fuse fuse2fs libfuse-dev libglib2.0-dev libseccomp-dev libtool \
        pkg-config runc squashfs-tools squashfs-tools-ng uidmap zlib1g-dev \
        python3-pip && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
RUN useradd -u $UID --create-home --home-dir /home/$USER --shell /bin/bash --user-group --groups adm,sudo $USER && \
    echo $USER:$USER | chpasswd && \
    echo "$USER ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers
RUN groupmod -g $GID $USER

# command to enable apt update, docker-ce version must be 20.XX.XX or higher.
RUN echo "Acquire::GzipIndexes \"true\"; Acquire::CompressionTypes::Order:: \"gz\";" > /etc/apt/apt.conf.d/docker-gzip-indexes

# activate 'USER'
RUN chown -R $USER /home/$USER
WORKDIR /home/$USER
USER ${USER}

# Install Go-lang
RUN cd $HOME && \
    export VERSION=1.21.6 OS=linux ARCH=amd64 && \
    wget https://dl.google.com/go/go$VERSION.$OS-$ARCH.tar.gz && \
    sudo tar -C /usr/local -xzvf go$VERSION.$OS-$ARCH.tar.gz && \
    rm go$VERSION.$OS-$ARCH.tar.gz
# Install Singularity
RUN cd $HOME && \
    export PATH=/usr/local/go/bin:${PATH}:${HOME}/go/bin && \
    export VERSION=4.1.0 && \
    wget https://github.com/sylabs/singularity/releases/download/v${VERSION}/singularity-ce-${VERSION}.tar.gz && \
    tar -xzf singularity-ce-${VERSION}.tar.gz && \
    cd singularity-ce-${VERSION} && \
    ./mconfig && \
    make -C ./builddir && \
    sudo make -C ./builddir install && \
    cd $HOME && \
    rm singularity-ce-${VERSION}.tar.gz
# Install Cerebras
RUN --mount=type=bind,source=Cerebras-SDK.tar.gz,target=Cerebras-SDK.tar.gz cd $HOME && \
    mkdir cs_sdk && \
    tar -C cs_sdk -xzvf Cerebras-SDK.tar.gz && \
    cd cs_sdk && \
    sha256sum --check sha256sum.txt
# Install python dep packages
RUN pip3 install --no-warn-script-location amplify lxml matplotlib numpy tqdm dvc[gdrive]

ENV GOPATH="$HOME/go"
ENV PATH="$HOME/cs_sdk:/usr/local/go/bin:$PATH:$GOPATH/bin:$HOME/.local/bin"

CMD ["/bin/bash"]
