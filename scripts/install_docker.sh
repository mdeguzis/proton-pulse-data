#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/install_docker.sh

Installs Docker Engine on Debian/Ubuntu-family systems using Docker's official
apt repository, then verifies the installation with Docker's hello-world image.

This script must be run with root privileges, for example:

  sudo bash scripts/install_docker.sh
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ "${EUID}" -ne 0 ]]; then
  echo "error: run this script as root (for example: sudo bash scripts/install_docker.sh)" >&2
  exit 1
fi

if [[ ! -r /etc/os-release ]]; then
  echo "error: cannot detect OS; /etc/os-release is missing" >&2
  exit 1
fi

. /etc/os-release

case "${ID:-}" in
  ubuntu|debian|pop)
    ;;
  *)
    echo "error: unsupported distro '${ID:-unknown}' for this helper" >&2
    echo "supported: Ubuntu, Debian, Pop!_OS" >&2
    exit 1
    ;;
esac

repo_family="ubuntu"
repo_codename="${UBUNTU_CODENAME:-${VERSION_CODENAME:-}}"

if [[ "${ID:-}" == "debian" ]]; then
  repo_family="debian"
fi

if [[ -z "${repo_codename}" ]]; then
  echo "error: VERSION_CODENAME not set in /etc/os-release" >&2
  exit 1
fi

apt-get update
apt-get install -y ca-certificates curl

# Remove distro-provided/conflicting packages per Docker's install docs.
for pkg in docker.io docker-compose docker-compose-v2 docker-doc podman-docker containerd runc; do
  apt-get remove -y "${pkg}" || true
done

install -m 0755 -d /etc/apt/keyrings
curl -fsSL "https://download.docker.com/linux/${repo_family}/gpg" -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc

cat > /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/${repo_family}
Suites: ${repo_codename}
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF

apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

if command -v systemctl >/dev/null 2>&1; then
  systemctl start docker || true
fi

echo "Docker installation complete."
echo "Running hello-world verification..."
docker run --rm hello-world
echo "Docker verification complete."
