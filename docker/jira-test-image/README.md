# Jira test image

Image used by the `pycontribs/jira` test suite. The Dockerfile in this
folder documents what it does and why; this README only covers usage.

## Build

```bash
docker build -t pycontribs/jira-test-image:8.17.1 docker/jira-test-image
```

## Run

```bash
docker run -dit -p 2990:2990 --name jira pycontribs/jira-test-image:8.17.1
```

`-dit` is required (AMPS exits without a controlling TTY). Default
credentials: `admin/admin`. First responsive request is typically
within ~3-5 minutes on a cold network.

### Jira version

`JIRA_VERSION` is overridable across Jira 8.x patch versions:

```bash
docker run -dit -p 2990:2990 -e JIRA_VERSION=8.17.0 --name jira \
  pycontribs/jira-test-image:8.17.1
```

Jira 9+ / 11+ are **not** supported here - the upstream addono pom.xml
is anchored to the 8.x dependency graph and fails Maven resolution
for newer majors. A future iteration will replace this wrapper with a
fully self-hosted multi-stage image that supports newer Jiras.
