# Thin wrap of addono/jira-software-standalone for the pycontribs/jira
# test suite.
#
# Two non-trivial things this image does on top of the addono base:
#
#   1. Pins the upstream by digest, not tag, so we are not at the mercy
#      of `:latest` shifting under us.
#   2. Adds `-DskipAllPrompts=true` to the AMPS invocation. Atlassian
#      shut down the Marketplace v1 REST endpoint AMPS hardcodes for
#      its SDK update check; without this flag, every fresh container
#      start fails with `FileNotFoundException` on
#      `https://marketplace.atlassian.com/rest/1.0/plugins/...`.
#
# JIRA_VERSION stays overridable - users can run any supported Jira
# version via `docker run -e JIRA_VERSION=11.0.1 ...`.

# https://hub.docker.com/r/addono/jira-software-standalone
# digest captured 2026-04-29; bump when intentionally upgrading the base.
FROM addono/jira-software-standalone@sha256:04326628dc4ac36b2bfc1d0f2ebe5ba3807c1ec9cf9b18307d3c2ad7222537e9

ARG JIRA_VERSION=8.17.1
ENV JIRA_VERSION=${JIRA_VERSION}

EXPOSE 2990

# atlas-run reads JIRA_VERSION from the env (the upstream image's pom
# uses ${env.JIRA_VERSION}). -DskipAllPrompts=true is a Maven system
# property forwarded through to the AMPS plugin.
ENTRYPOINT ["atlas-run", "-DskipAllPrompts=true"]
