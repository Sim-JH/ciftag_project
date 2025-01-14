# docker build -t ciftag-crawl-consumer -f ./docker/crawler/Dockerfile .
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
RUN pip install -r /src/module/docker/crawler/requirements.txt --ignore-installed

# Install Java for Kafka CLI
RUN apt-get update && apt-get install -y openjdk-11-jre

# Install Kafka CLI
RUN wget -qO- https://archive.apache.org/dist/kafka/3.5.1/kafka_2.13-3.5.1.tgz | tar -xz -C /opt/ && \
    mv /opt/kafka_2.13-3.5.1 /opt/kafka && \
    ln -s /opt/kafka/bin/* /usr/bin/ && \
    mkdir -p /opt/kafka/config && \
    echo "log4j.rootLogger=ERROR, stdout" > /opt/kafka/config/tools-log4j.properties && \
    echo "log4j.appender.stdout=org.apache.log4j.ConsoleAppender" >> /opt/kafka/config/tools-log4j.properties && \
    echo "log4j.appender.stdout.layout=org.apache.log4j.PatternLayout" >> /opt/kafka/config/tools-log4j.properties && \
    echo "log4j.appender.stdout.layout.ConversionPattern=%d{yyyy-MM-dd HH:mm:ss} %-5p %c{1}:%L - %m%n" >> /opt/kafka/config/tools-log4j.properties && \
    echo 'export KAFKA_LOG4J_OPTS="-Dlog4j.configuration=file:/opt/kafka/config/tools-log4j.properties"' >> /etc/profile

# Ensure Kafka CLI environment is loaded
ENV PATH=$PATH:/opt/kafka/bin
ENV CLASSPATH=/opt/kafka/libs/*
ENV KAFKA_LOG4J_OPTS="-Dlog4j.configuration=file:/opt/kafka/config/tools-log4j.properties"

# Install playwright
RUN playwright install
RUN playwright install-deps

# Install ciftag package
WORKDIR /src/module
RUN pip install -e .

# Dsize image
RUN apt-get clean && \
    rm -rf /var/lib/apt/lists/*
