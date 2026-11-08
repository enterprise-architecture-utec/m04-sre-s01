#!/usr/bin/env bash
set -euo pipefail

if command -v aws >/dev/null 2>&1; then
  echo "AWS CLI ya está instalado:"
  aws --version
  exit 0
fi

sudo apt-get update
sudo apt-get install -y ca-certificates curl unzip zip
tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

arch="$(dpkg --print-architecture)"
case "$arch" in
  amd64) aws_arch="x86_64" ;;
  arm64) aws_arch="aarch64" ;;
  *)
    echo "Arquitectura no soportada por este instalador: $arch" >&2
    exit 1
    ;;
esac

curl --fail --silent --show-error --location \
  "https://awscli.amazonaws.com/awscli-exe-linux-${aws_arch}.zip" \
  --output "$tmpdir/awscliv2.zip"
unzip -q "$tmpdir/awscliv2.zip" -d "$tmpdir"
sudo "$tmpdir/aws/install" --update
aws --version
