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

### Targeting a different Jira version

The Dockerfile is parameterised; every value that changes between Jira
majors is exposed as a `--build-arg`. `scripts/render-pom.sh` substitutes
the matching `@TOKEN@` placeholders in `plugin/pom.xml.template` into a
real `plugin/pom.xml` during the build, so the same source tree builds
Jira 8 through Jira 11.

```bash
docker build \
  --build-arg JAVA_IMAGE=eclipse-temurin:21-jdk-jammy \
  --build-arg AMPS_VERSION=9.11.2 \
  --build-arg JIRA_VERSION=11.3.4 \
  --build-arg SPRING_SCANNER_VERSION=6.0.0 \
  --build-arg COMPILE_FLOOR=17 \
  -t pycontribs/jira-test-image:11.3.4 docker/jira-test-image
```

Within a single major, `JIRA_VERSION` is also overridable at run-time
via `docker run -e JIRA_VERSION=...`:

```bash
docker run -dit -p 2990:2990 -e JIRA_VERSION=8.17.0 --name jira \
  pycontribs/jira-test-image:8.17.1
```

Defaults match the Jira version pycontribs server CI runs against
(`jira_server_ci.yml`), so a bare `docker build docker/jira-test-image`
produces the historical Jira 8.17.1 image.

#### Known-good build-arg combinations

Each row has been validated against a fresh `atlas-run` boot in the
companion `docker-jira-software-standalone` fork. Pass these as
`--build-arg` flags when building locally, or as workflow inputs in
`ghcr-publish.yml`.

| Jira version | `JAVA_IMAGE`                  | `AMPS_VERSION` | `SPRING_SCANNER_VERSION` | `TESTRUNNER_VERSION` | `COMPILE_FLOOR` |
|--------------|-------------------------------|----------------|--------------------------|----------------------|-----------------|
| 8.20.30      | `eclipse-temurin:8-jdk-jammy`  | `8.2.3`        | `2.1.17`                 | `2.0.16`             | `1.8`           |
| 9.12.34      | `eclipse-temurin:11-jdk-jammy` | `9.1.2`        | `2.2.6`                  | `2.0.16`             | `11`            |
| 10.3.19      | `eclipse-temurin:17-jdk-jammy` | `9.1.2`        | `2.2.6`                  | `2.0.16`             | `17`            |
| 11.3.4       | `eclipse-temurin:21-jdk-jammy` | `9.11.2`       | `6.0.0`                  | `2.0.16`             | `17`            |

Notes on the `AMPS_VERSION` line:

- `AMPS_VERSION` feeds two artefacts that share a release train but
  can drift: the SDK tarball (`atlassian-plugin-sdk`, consumed by
  `scripts/install-sdk.sh`) and the build extension
  (`com.atlassian.maven.plugins:jira-maven-plugin`, consumed by
  `plugin/pom.xml.template`). Both must resolve at the chosen
  version. Verify against
  [the SDK metadata](https://packages.atlassian.com/maven-external/com/atlassian/amps/atlassian-plugin-sdk/maven-metadata.xml)
  and
  [the plugin metadata](https://packages.atlassian.com/maven-external/com/atlassian/maven/plugins/jira-maven-plugin/maven-metadata.xml).
- For Jira 8 the SDK ships through `8.2.10` but the
  `jira-maven-plugin` 8.2.x line tops out at `8.2.3`, so `8.2.3` is
  the highest value that resolves on both paths.
- For Jira 9 the older 8.2.x SDK ships an `atlas-run` that calls
  `jira-maven-plugin:8.2.3` internally, which predates Jira 9 and
  fails to launch a 9.x instance. The 9.1.x line is the lowest AMPS
  that handles both Jira 9 and 10 cleanly (Spring 5 / `javax.*`
  baseline carries through; Maven 3.9 in SDK 9.1.x runs on Java 11+).
- `SPRING_SCANNER_VERSION` is Jakarta-locked to Jira's Spring major:
  2.1.x for Jira 8, 2.2.x for Jira 9-10, 6.x for Jira 11. Crossing
  the streams (2.x against `jakarta.*`, 6.x against `javax.*`)
  silently no-ops at scan time.

### Warmed variant

The Dockerfile is multi-stage. The default `unwarmed` target cold-boots
on every container start (~10–20 min depending on Jira major). The
`warmed` target bakes the result of one full `atlas-run` boot into the
image, so subsequent containers reach `/serverInfo` in ~1–2 min, at the
cost of ~25 min of build time:

```bash
docker build --target warmed -t pycontribs/jira-test-image:8.17.1-warm \
  docker/jira-test-image
```

### Publishing

`.github/workflows/ghcr-publish.yml` is a `workflow_dispatch` job that
exposes every build-arg as an input and publishes both the unwarmed
and warmed variants on every run. The optional `tag_latest` flag also
pushes `:<major>-latest` and `:<major>-warm-latest` floating tags.
Images are published under
`ghcr.io/<repository_owner>/jira-test-image:<jira_version>[-warm]`.
