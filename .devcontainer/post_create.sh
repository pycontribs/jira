#!/bin/bash
# This file is run from the .vscode folder
WORKSPACE_FOLDER=/workspaces/jira

# Start the Jira Server docker instance first so can be running while we initialise everything else
# Need to ensure this --version matches what is in CI
echo "Initiating jira server instance, use the docker extension to inspect the logs (takes around 10/15mins to startup)"
docker run -dit -p 2990:2990 --name jira addono/jira-software-standalone --version 8.17.1
echo "Once started up, Jira host port is forwarded and can be found on: localhost:2990/jira/"

# For Windows uses that have cloned into Windows' partition, we do this so that
# it doesn't show all the files as "changed" for having different line endings.
# As we use pre-commit for managing our line endings we do this to tell git we don't care
git config --global core.autocrlf input
git add .

# Install tox and pre-commit
pipx install pre-commit
pipx install tox

# Sanity check that we can run pre-commit env
pre-commit run mypy --all-files

# Set the PIP_CONSTRAINT env variable
PIP_CONSTRAINT=$WORKSPACE_FOLDER/constraints.txt
if [ -f "$PIP_CONSTRAINT" ]; then
    echo "$PIP_CONSTRAINT found, use 'unset PIP_CONSTRAINT' if you want to remove the constraints."
    echo "export PIP_CONSTRAINT="$PIP_CONSTRAINT"" >> ~/.bashrc && source ~/.bashrc
else
    echo "$PIP_CONSTRAINT was not found, dependencies are not controlled."
fi

# Install package in editable mode with test dependencies
pip install -e .[opt,test]
