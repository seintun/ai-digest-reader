#!/usr/bin/env bash
# Load .env without letting blank placeholder values clobber real environment values.
# Supports simple KEY=VALUE lines used by this project; comments and blank lines are ignored.

load_env_preserve_existing() {
  local env_file="${1:-.env}"
  [ -f "$env_file" ] || return 0

  local line key value existing
  while IFS= read -r line || [ -n "$line" ]; do
    # Trim leading whitespace for comment/blank detection.
    case "${line#${line%%[![:space:]]*}}" in
      ""|'#'*) continue ;;
    esac
    [[ "$line" == *"="* ]] || continue
    key="${line%%=*}"
    value="${line#*=}"
    key="${key//[[:space:]]/}"
    [[ "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || continue

    # Strip matching surrounding quotes for the simple .env format we use.
    if [[ "$value" == \"*\" && "$value" == *\" ]]; then
      value="${value:1:${#value}-2}"
    elif [[ "$value" == \'*\' && "$value" == *\' ]]; then
      value="${value:1:${#value}-2}"
    fi

    existing="${!key-}"
    if [ -n "$value" ] || [ -z "$existing" ]; then
      export "$key=$value"
    fi
  done < "$env_file"
}
