#!/usr/bin/env bash
# Substitute the @PLACEHOLDER@ tokens in plugin/pom.xml.template with
# build-arg values and emit plugin/pom.xml. Invoked by the Dockerfile
# during the base stage so a single source-of-truth template can serve
# every Jira major - the surrounding Dockerfile ARG block names every
# version pin that must change between majors.
#
# Args (positional, all required):
#   $1  AMPS version            (com.atlassian.maven.plugins:jira-maven-plugin)
#   $2  spring-scanner version  (atlassian-spring-scanner; must match
#                                Jira's Spring/Jakarta major)
#   $3  testrunner version      (atlassian-plugins-osgi-testrunner)
#   $4  compile floor           (Java source/target; matches runtime JDK)
#   $5  template path           (default: plugin/pom.xml.template)
#   $6  output path             (default: plugin/pom.xml)
#
# Adding a new placeholder is two edits: a new `-e` to the sed call,
# and a new ARG block in the Dockerfile that surfaces the value.
# A new placeholder NOT wired into the sed call will trip the drift
# guard below, since it survives untouched in the rendered pom.
set -euo pipefail

AMPS_VERSION="${1:?AMPS version required}"
SPRING_SCANNER_VERSION="${2:?spring-scanner version required}"
TESTRUNNER_VERSION="${3:?testrunner version required}"
COMPILE_FLOOR="${4:?compile floor required}"
TEMPLATE="${5:-plugin/pom.xml.template}"
OUTPUT="${6:-plugin/pom.xml}"

if [ ! -f "$TEMPLATE" ]; then
    echo "render-pom: template not found at $TEMPLATE" >&2
    exit 1
fi

sed \
    -e "s|@AMPS_VERSION@|${AMPS_VERSION}|g" \
    -e "s|@SPRING_SCANNER_VERSION@|${SPRING_SCANNER_VERSION}|g" \
    -e "s|@TESTRUNNER_VERSION@|${TESTRUNNER_VERSION}|g" \
    -e "s|@COMPILE_FLOOR@|${COMPILE_FLOOR}|g" \
    "$TEMPLATE" > "$OUTPUT"

# Drift guard: any `@TOKEN@` sitting inside an XML element (or as the
# value of an attribute) survived sed and is therefore a placeholder
# the substitution block above forgot. The XML-context anchors
# (`>@...@<`, `="@...@"`) keep this from false-positive-ing on the
# bare `@ARG_NAME@` prose example in the template's header comment.
if grep -nE '(>@[A-Z_]+@<|="@[A-Z_]+@")' "$OUTPUT" >&2; then
    echo "render-pom: unsubstituted placeholder(s) remain in $OUTPUT" >&2
    exit 1
fi
