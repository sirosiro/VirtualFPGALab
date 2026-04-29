#!/bin/bash
PROJECT_ROOT=$(cd "$(dirname "$0")/../../.." && pwd)
${PROJECT_ROOT}/tests/scenario_runner.sh $(dirname "$0") "$@"
