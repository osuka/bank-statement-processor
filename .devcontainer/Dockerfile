FROM python:3.7-slim
LABEL maintainer="noone@localhost"

# Avoid warnings by switching to noninteractive
ENV DEBIAN_FRONTEND=noninteractive

# This container intentionally runs with a non privileged user
# without sudo or password
ENV THEUSER=python
RUN useradd -m ${THEUSER}
RUN mkdir /workspace && chown -R ${THEUSER} /workspace

# Install here any tool we may need to run, from extensions or from the terminal etc
# This allows us to isolate the running environment
# We install pylint so the python Visual Studio Code extension can use it

# for apt packages
RUN apt-get update && apt-get upgrade -y && \
  apt-get install -y apt-transport-https git && \
  apt-get autoremove -y && apt-get clean -y && rm -rf /var/lib/apt/lists/*

# for python dependencies (normal ones can be installed from requirements.txt manually)
RUN pip install pylint

# Switch back to dialog for any ad-hoc use of apt-get
ENV DEBIAN_FRONTEND=dialog

# we don't want full root access inside the docker container but pip will want to write in /usr/local
RUN chown -R ${THEUSER} /usr/local

# everything else is done using this user
USER ${THEUSER}
