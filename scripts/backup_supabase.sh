#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

usage() {
  cat <<'EOF'
Usage: scripts/backup_supabase.sh [--linked] [--label LABEL] [--output-dir DIR]

Creates a logical backup of a Supabase database using the Supabase CLI:
  - roles.sql   custom cluster roles
  - schema.sql  schema-only dump
  - data.sql    data-only dump with COPY statements

Connection options:
  1. Set SUPABASE_DB_URL to dump from an explicit connection string, or
  2. pass --linked to use an already-linked Supabase project.

Environment:
  SUPABASE_DB_URL         Percent-encoded Postgres connection string.
  SUPABASE_ACCESS_TOKEN   Supabase personal access token.
  SUPABASE_BACKUP_DIR     Root output directory. Default: data/supabase
  SUPABASE_BACKUP_LABEL   Backup folder name. Default: UTC timestamp

Examples:
  SUPABASE_DB_URL='postgresql://...' scripts/backup_supabase.sh
  scripts/backup_supabase.sh --linked
  scripts/backup_supabase.sh --linked --label nightly
EOF
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "error: required command not found: $1" >&2
    exit 1
  fi
}

resolve_supabase_cmd() {
  if command -v supabase >/dev/null 2>&1; then
    SUPABASE_CMD=(supabase)
    return
  fi

  if command -v npx >/dev/null 2>&1; then
    SUPABASE_CMD=(npx --yes supabase)
    return
  fi

  echo "error: Supabase CLI not found. Install 'supabase' or ensure 'npx' is available." >&2
  echo "note: ~/.supabase stores CLI auth state, not the executable itself." >&2
  exit 1
}

print_login_hint() {
  cat >&2 <<'EOF'
Supabase CLI auth is not configured yet.

Expected auth locations:
  - ~/.supabase/access-token        current CLI layout
  - ~/.supabase/.supabase           migrated legacy single-file token
  - SUPABASE_ACCESS_TOKEN           environment override

If you already have a token string, you can export it temporarily:

  export SUPABASE_ACCESS_TOKEN=your_token_here

Or log in with the CLI:

  npx --yes supabase login

Then rerun:

  make backup-supabase
EOF
}

print_docker_install_hint() {
  cat >&2 <<'EOF'
Docker is required by the Supabase CLI for this backup flow.

Supabase CLI local-dev docs:
  https://supabase.com/docs/guides/local-development/cli/getting-started

In this repo, install it with:

  make install-docker

Or install/verify manually:

  docker info

If Docker is installed but not running, start the daemon and rerun:

  make backup-supabase
EOF
}

print_docker_start_hint() {
  cat >&2 <<'EOF'
Docker is installed, but the daemon is not reachable.

Check it with:

  docker info

If you're using Docker Engine on Linux, a common fix is:

  sudo systemctl start docker

Then rerun:

  make backup-supabase
EOF
}

print_docker_permission_hint() {
  cat >&2 <<'EOF'
Docker is installed and the daemon appears present, but the current user cannot
access the Docker socket.

Typical Linux fix:

  sudo usermod -aG docker "$USER"

Then start a new shell session (or log out/in) and verify:

  docker info

Then rerun:

  make backup-supabase
EOF
}

attempt_docker_install() {
  local install_script="${REPO_ROOT}/scripts/install_docker.sh"
  if [[ ! -x "${install_script}" ]]; then
    return 1
  fi

  echo "Docker not found. Attempting automatic install via ${install_script}..."
  sudo bash "${install_script}"
}

attempt_docker_start() {
  echo "Docker daemon not reachable. Attempting to start it..."
  sudo systemctl start docker
}

print_link_hint() {
  cat >&2 <<'EOF'
This repo is not linked to a Supabase project yet.

Run one of these first:

  npx --yes supabase link

If your project requires a database password during linking:

  npx --yes supabase link --project-ref <your-project-ref> --password <your-db-password>

Then rerun:

  make backup-supabase
EOF
}

attempt_supabase_link() {
  if [[ ! -t 0 || ! -t 1 ]]; then
    return 1
  fi

  echo "Supabase link metadata is missing. Attempting interactive relink..."
  (
    cd "${REPO_ROOT}"
    "${SUPABASE_CMD[@]}" link
  )
}

load_supabase_access_token() {
  if [[ -n "${SUPABASE_ACCESS_TOKEN:-}" ]]; then
    return
  fi

  local token_dir="${HOME}/.supabase"
  local token_file="${token_dir}/access-token"
  local migrated_legacy_file="${token_dir}/.supabase"
  local legacy_file="${HOME}/.supabase"
  local token=""

  if [[ -f "${token_file}" ]]; then
    token="$(tr -d '\r\n' < "${token_file}")"
  elif [[ -f "${migrated_legacy_file}" ]]; then
    token="$(tr -d '\r\n' < "${migrated_legacy_file}")"
  elif [[ -f "${legacy_file}" ]]; then
    token="$(tr -d '\r\n' < "${legacy_file}")"
  fi

  if [[ -n "${token}" ]]; then
    export SUPABASE_ACCESS_TOKEN="${token}"
  fi
}

ensure_linked_project() {
  local linked_ref_file="${REPO_ROOT}/supabase/.temp/project-ref"
  local linked_project_json="${REPO_ROOT}/supabase/.temp/linked-project.json"

  if [[ -s "${linked_ref_file}" ]]; then
    return
  fi

  if [[ -s "${linked_project_json}" ]]; then
    return
  fi

  if attempt_supabase_link; then
    if [[ -s "${linked_ref_file}" ]] || [[ -s "${linked_project_json}" ]]; then
      return
    fi
  fi

  print_link_hint
  exit 1
}

ensure_docker_ready() {
  if ! command -v docker >/dev/null 2>&1; then
    if ! attempt_docker_install; then
      print_docker_install_hint
      exit 1
    fi
    if ! command -v docker >/dev/null 2>&1; then
      print_docker_install_hint
      exit 1
    fi
  fi

  local docker_output=""
  if ! docker_output="$(docker info 2>&1)"; then
    printf '%s\n' "${docker_output}" >&2
    if [[ "${docker_output}" == *"permission denied while trying to connect to the docker API socket"* ]] \
      || [[ "${docker_output}" == *"permission denied while trying to connect to the docker API at unix:///var/run/docker.sock"* ]]; then
      print_docker_permission_hint
      exit 1
    fi
    if ! attempt_docker_start; then
      print_docker_start_hint
      exit 1
    fi
    if ! docker_output="$(docker info 2>&1)"; then
      printf '%s\n' "${docker_output}" >&2
      print_docker_start_hint
      exit 1
    fi
  fi
}

linked=false
backup_label="${SUPABASE_BACKUP_LABEL:-}"
backup_root="${SUPABASE_BACKUP_DIR:-${REPO_ROOT}/data/supabase}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --linked)
      linked=true
      shift
      ;;
    --label)
      backup_label="${2:-}"
      if [[ -z "${backup_label}" ]]; then
        echo "error: --label requires a value" >&2
        exit 1
      fi
      shift 2
      ;;
    --output-dir)
      backup_root="${2:-}"
      if [[ -z "${backup_root}" ]]; then
        echo "error: --output-dir requires a value" >&2
        exit 1
      fi
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "error: unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

require_command tar
resolve_supabase_cmd
load_supabase_access_token

declare -a source_args
source_mode=""
if [[ -n "${SUPABASE_DB_URL:-}" ]]; then
  source_args=(--db-url "${SUPABASE_DB_URL}")
  source_mode="db-url"
elif [[ "${linked}" == true ]]; then
  if [[ -z "${SUPABASE_ACCESS_TOKEN:-}" ]]; then
    print_login_hint
    exit 1
  fi
  ensure_linked_project
  source_args=(--linked)
  source_mode="linked"
else
  echo "error: set SUPABASE_DB_URL or pass --linked" >&2
  exit 1
fi

ensure_docker_ready

if [[ -z "${backup_label}" ]]; then
  backup_label="$(date -u +%Y%m%dT%H%M%SZ)"
fi

if [[ "${backup_root}" != /* ]]; then
  backup_root="${REPO_ROOT}/${backup_root}"
fi

mkdir -p "${backup_root}"

backup_dir="${backup_root}/${backup_label}"
if [[ -e "${backup_dir}" ]]; then
  echo "error: backup output already exists: ${backup_dir}" >&2
  exit 1
fi
mkdir -p "${backup_dir}"

cleanup_backup_dir() {
  if [[ -d "${backup_dir:-}" ]]; then
    rm -rf "${backup_dir}"
  fi
}

trap cleanup_backup_dir ERR

run_dump() {
  local target_file="$1"
  shift
  echo "==> writing ${target_file}"
  local output=""
  local status=0
  if ! output="$("${SUPABASE_CMD[@]}" db dump "${source_args[@]}" -f "${backup_dir}/${target_file}" "$@" 2>&1)"; then
    status=$?
    printf '%s\n' "${output}" >&2
    if [[ "${source_mode}" == "linked" ]] && [[ "${output}" == *"Cannot find project ref. Have you run supabase link?"* ]]; then
      print_link_hint
    fi
    exit "${status}"
  fi
  if [[ -n "${output}" ]]; then
    printf '%s\n' "${output}"
  fi
}

echo "Creating Supabase backup in ${backup_dir}"

run_dump "roles.sql" --role-only
run_dump "schema.sql"
run_dump "data.sql" --data-only --use-copy

cat > "${backup_dir}/manifest.txt" <<EOF
created_at_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)
source_mode=${source_mode}
backup_label=${backup_label}
files=roles.sql,schema.sql,data.sql
EOF

archive_path="${backup_dir}.tar.gz"
tar -C "${backup_root}" -czf "${archive_path}" "${backup_label}"
trap - ERR

echo "Backup complete:"
echo "  directory: ${backup_dir}"
echo "  archive:   ${archive_path}"
