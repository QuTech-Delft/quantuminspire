FROM python:3.11-bullseye as base

# Build environment variables
ENV DEBIAN_FRONTEND noninteractive

# Set up user
ARG USER=vagrant
ENV PATH /home/${USER}/.local/bin:$PATH
RUN groupadd -r ${USER} && \
    useradd -m -r -s /bin/bash -g ${USER} ${USER}

RUN apt-get update -y && \
    apt-get install -y --no-install-recommends \
    sudo && \
    apt-get clean && \
    echo -n "${USER}:${USER}" | chpasswd && \
    echo "${USER} ALL = NOPASSWD: ALL" > /etc/sudoers.d/${USER} && \
    chmod 440 /etc/sudoers.d/${USER}

USER ${USER}

RUN pip install --upgrade pip wheel setuptools tox

# Install poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

FROM base as vscode

CMD ["/bin/sh", "-c", "'while sleep 1000; do :; done'"]

FROM base as vagrant

USER root

RUN apt-get update -y && \
    apt-get install -y --no-install-recommends \
    ssh \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    openssh-client && \
    apt-get clean

RUN sed -i -e 's/Defaults.*requiretty/#&/' /etc/sudoers && \
    sed -i -e 's/\(UsePAM \)yes/\1 no/' /etc/ssh/sshd_config && \
    mkdir -p /var/run/sshd /home/${USER}/.ssh/

RUN curl https://raw.githubusercontent.com/mitchellh/vagrant/master/keys/vagrant.pub >> /home/${USER}/.ssh/authorized_keys

EXPOSE 22

CMD ["/usr/sbin/sshd", "-D"]
