#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
JIRA_URL=http://127.0.0.1:2990/jira/secure/Dashboard.jspa
cd "$DIR"
rm jira.log
atlas-run-standalone --product jira --http-port 2990 \
    -B -nsu -o --threads 2.0C </dev/zero >jira.log 2>&1 &

printf "Waiting for JIRA to start respinding on $JIRA_URL "
until $(curl --output /dev/null --silent --head --fail $JIRA_URL); do
    printf '.'
    sleep 5
done
