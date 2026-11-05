FROM ubuntu:24.04
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends blender ca-certificates && rm -rf /var/lib/apt/lists/*
ENV HOME=/tmp
WORKDIR /tmp
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends python3-numpy && rm -rf /var/lib/apt/lists/*
