#!/bin/bash
set -ex
kill $(ps -o pid,command|grep atlassian-plugin-sdk|grep java|awk '{print $1}')
#ps -o pid,command|grep atlassian-plugin-sdk|grep java|awk '{kill -9 $1;}'
