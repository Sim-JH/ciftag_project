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
    iputils-ping \
    httping \
    locales \
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

# Install python packages
RUN python3 -m ensurepip --upgrade
RUN pip install --upgrade pip setuptools
COPY ./requirements.txt /src/module/requirements.txt
RUN pip install -r /src/module/requirements.txt --ignore-installed

# Install playwright
RUN playwright install
RUN playwright install-deps

# Install ciftag package
COPY . /src/module
WORKDIR /src/module
RUN pip install -e .

# Dsize image
RUN apt-get clean && \
    rm -rf /var/lib/apt/lists/*

CMD sh ciftag/fargate/init.sh