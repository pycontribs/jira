# See here for image contents: https://github.com/devcontainers/images/blob/main/src/base-ubuntu/.devcontainer/Dockerfile

# [Choice] Ubuntu version: https://github.com/devcontainers/images/tree/main/src/base-ubuntu
ARG VARIANT="jammy"
FROM mcr.microsoft.com/vscode/devcontainers/base:${VARIANT}

# [Optional] Uncomment this section to install additional OS packages.
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
     && apt-get -y install --no-install-recommends libkrb5-dev
