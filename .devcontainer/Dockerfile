# See here for image contents: https://github.com/microsoft/vscode-dev-containers/tree/v0.241.1/containers/python-3/.devcontainer/base.Dockerfile

ARG VARIANT="3.10-bullseye"
FROM mcr.microsoft.com/vscode/devcontainers/python:0-${VARIANT}

ENV DEBIAN_FRONTEND noninteractive
ENV PATH /home/vscode/.local/bin:$PATH

# [Optional] If your pip requirements rarely change, uncomment this section to add them to the image.
# COPY requirements.txt /tmp/pip-tmp/
# RUN pip3 --disable-pip-version-check --no-cache-dir install -r /tmp/pip-tmp/requirements.txt \
#    && rm -rf /tmp/pip-tmp

# Install additional OS packages.
RUN apt-get update && \
    apt-get -y install --no-install-recommends \
    libsm6 libxext6

USER vscode
RUN curl -sSL https://install.python-poetry.org | python3 - && \
    poetry config virtualenvs.create false