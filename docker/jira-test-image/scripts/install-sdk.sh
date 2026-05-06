#!/usr/bin/env bash
# Install the Atlassian Plugin SDK from the maven-external tarball.
# Apt path was retired Feb 2018, so curl-extract is the only supported
# install pattern. Tarball URL pattern is stable across AMPS 9.x.
#
# Artifact coordinates: groupId=com.atlassian.amps,
# artifactId=atlassian-plugin-sdk. Verify a chosen version is published
# at:
#   https://packages.atlassian.com/maven-external/com/atlassian/amps/atlassian-plugin-sdk/maven-metadata.xml
#
# Args:
#   $1  AMPS version (e.g. 9.11.2)
set -euo pipefail

AMPS_VERSION="${1:?AMPS version required}"

apt-get update
apt-get install -y --no-install-recommends ca-certificates curl
rm -rf /var/lib/apt/lists/*

mkdir -p /opt/atlassian-plugin-sdk

curl -fsSL \
    "https://packages.atlassian.com/maven-external/com/atlassian/amps/atlassian-plugin-sdk/${AMPS_VERSION}/atlassian-plugin-sdk-${AMPS_VERSION}.tar.gz" \
  | tar -xz -C /opt/atlassian-plugin-sdk --strip-components=1

chmod -R a+rx /opt/atlassian-plugin-sdk/bin
