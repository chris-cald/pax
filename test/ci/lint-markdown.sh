#!/usr/bin/env sh
set -eu

run_markdownlint() {
  NPM_CONFIG_CACHE=.npm-cache npx --yes --package markdownlint-cli2@0.21.0 markdownlint-cli2 "$@"
}

has_targets=0
expect_option_value=0
for arg in "$@"; do
  if [ "$expect_option_value" -eq 1 ]; then
    expect_option_value=0
    continue
  fi

  case "$arg" in
    --config|-c)
      expect_option_value=1
      ;;
    --config=*)
      ;;
    -*)
      ;;
    *)
      has_targets=1
      ;;
  esac
done

if [ "$has_targets" -eq 1 ]; then
  run_markdownlint "$@"
else
  run_markdownlint "$@" "**/*.md"
fi
