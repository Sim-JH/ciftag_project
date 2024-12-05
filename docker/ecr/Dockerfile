# docker build -t ciftag-crawl-consumer -f ./docker/ecr/Dockerfile .
FROM ubuntu:22.04

# Set the noninteractive frontend to avoid prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Set encoding
ENV LANG en_US.UTF-8
ENV LC_ALL en_US.UTF-8

# Base pkg
RUN apt-get update && \
    apt-get install --no-install-recommends -y --quiet \
    apt-utils \
    gnupg \
    software-properties-common \
    wget \
    unzip \
    zip \
    vim \
    curl \
    iputils-ping \
    httping \
    locales \
    iptables \
    libxcb1 \
    libfftw3-3 \
    libxmu6 \
    libxcomposite-dev \
    imagemagick \
    x11-apps && \
    locale-gen en_US.UTF-8

# Install python 3.12
RUN apt-get update && \
    add-apt-repository ppa:deadsnakes/ppa && \
    apt-get update && \
    apt-get install -y python3.12-venv python3.12-distutils python3-pip && \
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1

# Install opencv dependencies
RUN apt-get update && \
    apt-get install libgl1-mesa-glx -y

# move module first
COPY . /src/module
RUN rm -rf /src/module/ciftag/ml && rm -f /src/module/requirements.txt

# Install python packages & overwright requirements
RUN python3 -m ensurepip --upgrade
RUN pip install --upgrade pip setuptools
RUN pip install -r /src/module/docker/ecr/requirements.txt --ignore-installed

# Install Java for Kafka CLI
RUN apt-get update && apt-get install -y openjdk-11-jre

# Install Kafka CLI
RUN wget -qO- https://downloads.apache.org/kafka/3.8.1/kafka_2.13-3.8.1.tgz | tar -xz -C /opt/ && \
    ln -s /opt/kafka_2.13-3.8.1 /opt/kafka && \
    ln -s /opt/kafka/bin/* /usr/bin/ && \
    rm -rf /opt/kafka_2.13-3.4.0.tgz

# Install playwright
RUN playwright install
RUN playwright install-deps

# Install ciftag package
WORKDIR /src/module
RUN pip install -e .

# Dsize image
RUN apt-get clean && \
    rm -rf /var/lib/apt/lists/*

CMD sh ciftag/fargate/init.sh