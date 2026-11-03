#!/bin/sh
# Instala el backend de Armario en proot Ubuntu (aarch64), sin Docker.
# Ejecutar dentro del Ubuntu de proot, no en Termux pelado.
# Uso: ARMARIO_ROOT=~/armario-virtual sh deploy/gt2/install.sh
set -eu

ROOT="${ARMARIO_ROOT:-$HOME/armario-virtual}"
BACKEND="$ROOT/backend"
VENV="${ARMARIO_VENV:-$HOME/.venv/armario}"
ENV_FILE="${ARMARIO_ENV:-$HOME/armario.env}"

if [ ! -d "$BACKEND/app" ]; then
  echo "No encuentro el backend en $BACKEND. Clona el repo y exporta ARMARIO_ROOT." >&2
  exit 1
fi

if [ "$(id -u)" -eq 0 ]; then
  apt-get update
  apt-get install -y python3 python3-venv python3-pip build-essential libpq-dev redis-server curl ca-certificates
fi

python3 -m venv "$VENV"
"$VENV/bin/pip" install --upgrade pip
"$VENV/bin/pip" install -r "$BACKEND/requirements.txt"

if [ ! -f "$ENV_FILE" ]; then
  cp "$ROOT/deploy/gt2/env.example" "$ENV_FILE"
  echo "Creado $ENV_FILE. Rellena SECRET_KEY y DATABASE_URL antes de migrar." >&2
  exit 0
fi

set -a
# shellcheck disable=SC1090
. "$ENV_FILE"
set +a

mkdir -p "${STORAGE_PATH:-/var/lib/armario}"
cd "$BACKEND"
"$VENV/bin/python" -m alembic upgrade head

echo "Listo. Copia deploy/gt2/runit/* al directorio de servicios de runit y arranca redis, armario-api y armario-worker."
echo "No instales el image-worker: rembg queda apagado en el teléfono."
