#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

REPORT_DIR="reports"
mkdir -p "$REPORT_DIR"

SUITE="${1:-}"

require_docker_runtime() {
    : "${RUNTIME_PROJECT_NAME:?RUNTIME_PROJECT_NAME must be set for Docker runtime tests}"
    : "${RUNTIME_ENV_FILE:?RUNTIME_ENV_FILE must be set for Docker runtime tests}"

    if [[ ! -f "$RUNTIME_ENV_FILE" ]]; then
        echo "RUNTIME_ENV_FILE does not exist: $RUNTIME_ENV_FILE" >&2
        exit 2
    fi
}

case "$SUITE" in

    static)
        echo "Running static tests..."

        python -m pytest \
            -m "unit or config" \
            --junitxml="$REPORT_DIR/static.xml"
        ;;

    runtime)
        echo "Running public runtime tests..."

        : "${BASE_URL:?BASE_URL must be set for runtime tests}"

        python -m pytest \
            -m "health or smoke or assets or routing" \
            --junitxml="$REPORT_DIR/runtime.xml"
        ;;

    integration)
        echo "Running functional Docker integration tests..."

        : "${BASE_URL:?BASE_URL must be set for integration tests}"
        require_docker_runtime

        python -m pytest \
            -m "integration and docker and not network" \
            --junitxml="$REPORT_DIR/integration.xml"
        ;;

    network)
        echo "Running network isolation tests..."

        require_docker_runtime

        python -m pytest \
            -m "integration and docker and network" \
            --junitxml="$REPORT_DIR/network.xml"
        ;;

    green)
        echo "Running all currently green test groups..."

        "$0" static
        "$0" runtime
        "$0" integration
        ;;

    *)
        echo "Usage:"
        echo "  $0 static"
        echo "  $0 runtime"
        echo "  $0 integration"
        echo "  $0 network"
        echo "  $0 green"
        exit 2
        ;;
esac