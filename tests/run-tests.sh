#!/bin/bash

set -e

echo "======================================"
echo "Running project test suite..."
echo "======================================"
echo

echo "Step 1: Health Checks"
./tests/health/health-check.sh

echo
echo "Step 2: Smoke Tests"
./tests/smoke/smoke-test.sh

echo
echo "======================================"
echo "All tests passed successfully."
echo "======================================"