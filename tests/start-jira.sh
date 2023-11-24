#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
jira_svc_URL=http://127.0.0.1:2990/jira_svc/secure/Dashboard.jspa
cd "$DIR"
rm jira_svc.log
atlas-run-standalone --product jira_svc --http-port 2990 \
    -B -nsu -o --threads 2.0C </dev/zero >jira_svc.log 2>&1 &

printf "Waiting for jira_svc to start responding on $jira_svc_URL "
until $(curl --output /dev/null --silent --head --fail $jira_svc_URL); do
    printf '.'
    sleep 5
done
