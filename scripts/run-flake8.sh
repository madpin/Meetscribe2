#!/bin/bash
set -e

echo "Running flake8 critical checks..."
flake8 app/ tests/ --count --select=E9,F63,F7,F82 --show-source --statistics

echo "Running flake8 style checks..."
flake8 app/ tests/ --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
