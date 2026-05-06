# Self-hosted multi-stage image for the pycontribs/jira test suite.
# Replaces the previous thin wrapper around addono/jira-software-standalone:
# every value that changes between Jira majors is exposed as an ARG,
# so the same Dockerfile boots Jira 8 (this suite's historic target)
# all the way through Jira 11 (Jakarta / Spring 6) by flipping ARGs.
#
# Defaults pin to Jira 8.17.1 - the version used by jira_server_ci.yml -
# so the existing CI step `docker build docker/jira-test-image` produces
# the same image without needing per-major overrides.
#
# Why the move off the addono base:
#   1. The upstream image is anchored to its own pom, which only
#      resolves the Jira 8.x dependency graph. Newer majors fail
#      Maven resolution and silently fall back to 8.x at runtime.
#   2. The companion ghcr-publish.yml workflow exposes every ARG as
#      a workflow_dispatch input and publishes both unwarmed and
#      warmed variants per dispatch.

# === ARGs =====================================================================
# Java runtime image. Jira 11.x = JDK 21; 10.x = JDK 17; 9.x = JDK 11;
# 8.x = JDK 8. https://confluence.atlassian.com/adminjiraserver/supported-platforms-938846830.html
ARG JAVA_IMAGE=eclipse-temurin:8-jdk-jammy

# AMPS (Atlassian Maven Plugin Suite). Consumed in two places:
#   - install-sdk.sh against the atlassian-plugin-sdk tarball
#   - plugin/pom.xml.template against jira-maven-plugin
# The two artifacts share a release train but can drift; verify both:
#   https://packages.atlassian.com/maven-external/com/atlassian/amps/atlassian-plugin-sdk/maven-metadata.xml
#   https://packages.atlassian.com/maven-external/com/atlassian/maven/plugins/jira-maven-plugin/maven-metadata.xml
# Known-good combos: 8.2.3 (Jira 8), 9.1.2 (Jira 9 + 10), 9.11.2 (Jira 11).
ARG AMPS_VERSION=8.2.3

# Jira version baked as build-time default. Same image can boot any
# patch within the major via `docker run -e JIRA_VERSION=...`.
# The ENV that surfaces this to atlas-run lives inside the base stage
# (ENV is not legal before the first FROM).
ARG JIRA_VERSION=8.17.1

# atlassian-spring-scanner. Jakarta-locked to Jira's Spring major:
#   2.1.x = Jira 8 (Spring 5 / javax.*)
#   2.2.x = Jira 9 + 10 (Spring 5 / javax.*)
#   6.x   = Jira 11 (Spring 6 / Jakarta EE 10)
# Crossing the streams (2.x against jakarta.*, 6.x against javax.*) silently no-ops.
ARG SPRING_SCANNER_VERSION=2.1.17

# atlassian-plugins-osgi-testrunner. Stable across Jira 8-11 on the 2.0.x line.
ARG TESTRUNNER_VERSION=2.0.16

# Java compile floor for the plugin jar. Match the runtime JDK so the
# resulting class files load on the target Jira's classloader.
ARG COMPILE_FLOOR=1.8

# === base =====================================================================
# Common scaffolding shared by `unwarmed`, `warmer`, and `warmed`.
FROM ${JAVA_IMAGE} AS base

# Redeclare ARGs after FROM so they're visible in this stage.
ARG AMPS_VERSION
ARG JIRA_VERSION
ARG SPRING_SCANNER_VERSION
ARG TESTRUNNER_VERSION
ARG COMPILE_FLOOR

ENV JIRA_VERSION=${JIRA_VERSION}

ARG DEBIAN_FRONTEND=noninteractive
ENV PATH=/opt/atlassian-plugin-sdk/bin:${PATH}

# SDK install. Tarball is the only supported path - the apt repo at
# packages.atlassian.com/atlassian-sdk-deb was retired Feb 2018.
COPY scripts/install-sdk.sh /tmp/install-sdk.sh
RUN bash /tmp/install-sdk.sh "${AMPS_VERSION}" && rm /tmp/install-sdk.sh

WORKDIR /opt/jira-plugin
COPY plugin/ ./
COPY scripts/render-pom.sh /tmp/render-pom.sh
RUN bash /tmp/render-pom.sh \
        "${AMPS_VERSION}" \
        "${SPRING_SCANNER_VERSION}" \
        "${TESTRUNNER_VERSION}" \
        "${COMPILE_FLOOR}" \
        pom.xml.template \
        pom.xml \
    && rm /tmp/render-pom.sh pom.xml.template

EXPOSE 2990

# === warmer ===================================================================
# Build-time-only stage. Runs atlas-run in the background, polls
# /rest/api/2/serverInfo until 200, SIGTERMs the JVM, validates that
# the warmed paths exist + are non-empty. The `warmed` stage COPY-s
# those paths from this stage's filesystem.
FROM base AS warmer
COPY scripts/warm.sh /tmp/warm.sh
RUN bash /tmp/warm.sh && rm /tmp/warm.sh

# === warmed ===================================================================
# Runtime stage with the Maven cache + unpacked Jira webapp baked in.
# Caller picks this via `docker build --target warmed`. Cold-boot
# becomes ~1-2min instead of ~10-20min because Maven downloads + war
# unpack + initial DB schema are pre-populated. -o (offline) keeps
# Maven from reaching out at runtime since the cache is fully populated.
FROM base AS warmed
COPY --from=warmer /root/.m2 /root/.m2
COPY --from=warmer /opt/jira-plugin/target /opt/jira-plugin/target
# -DskipAllPrompts=true: AMPS hardcodes a call to the shut-down
# Atlassian Marketplace v1 endpoint at startup. This flag makes the
# resulting 404 non-fatal so the boot proceeds.
# Caller MUST run with -it; atlas-run exits without a TTY.
ENTRYPOINT ["atlas-run", "-DskipAllPrompts=true", "-o"]

# === unwarmed (default target) ================================================
# Default `docker build .` target. Boots cold every container start
# (~10-20min depending on Jira major). Use `--target warmed` to opt
# into the pre-baked variant when the upfront ~25min build cost is
# acceptable.
FROM base AS unwarmed
# -DskipAllPrompts=true: same Marketplace v1 endpoint workaround as
# above. Caller MUST run with -it; atlas-run exits without a TTY.
ENTRYPOINT ["atlas-run", "-DskipAllPrompts=true"]
