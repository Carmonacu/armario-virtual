#!/bin/sh
# Ventana nocturna: para Armario, arranca llama-server, genera los conjuntos
# del día siguiente, apaga el modelo y vuelve a levantar el API.
#
# Los comandos por defecto llaman a ~/bin/mode. Ajústalos si el script del
# teléfono usa otros argumentos:
#   ARMARIO_STOP_CMD, ARMARIO_START_CMD, LLM_START_CMD, LLM_STOP_CMD
#
# Pensado para cron, dentro de proot Ubuntu, por ejemplo:
#   0 23 * * * /bin/sh $HOME/armario-virtual/deploy/gt2/nightly.sh >>$HOME/armario-nightly.log 2>&1
set -eu

ROOT="${ARMARIO_ROOT:-$HOME/armario-virtual}"
BACKEND="$ROOT/backend"
VENV="${ARMARIO_VENV:-$HOME/.venv/armario}"
ENV_FILE="${ARMARIO_ENV:-$HOME/armario.env}"
PYTHON="$VENV/bin/python"

ARMARIO_STOP_CMD="${ARMARIO_STOP_CMD:-mode stop armario}"
ARMARIO_START_CMD="${ARMARIO_START_CMD:-mode start armario}"
LLM_START_CMD="${LLM_START_CMD:-mode start llm}"
LLM_STOP_CMD="${LLM_STOP_CMD:-mode stop llm}"
LLM_URL="${LLM_URL:-http://127.0.0.1:8080/v1}"
LLM_WAIT_SECONDS="${LLM_WAIT_SECONDS:-180}"

stopped_armario=0
started_llm=0

cleanup() {
  status=$?
  if [ "$started_llm" -eq 1 ]; then
    sh -c "$LLM_STOP_CMD" || true
    started_llm=0
  fi
  if [ "$stopped_armario" -eq 1 ]; then
    sh -c "$ARMARIO_START_CMD" || true
    stopped_armario=0
  fi
  exit "$status"
}
trap cleanup EXIT INT TERM

if [ -f "$ENV_FILE" ]; then
  set -a
  # shellcheck disable=SC1090
  . "$ENV_FILE"
  set +a
fi

echo "$(date -Is) parando servicios de armario"
sh -c "$ARMARIO_STOP_CMD"
stopped_armario=1

echo "$(date -Is) arrancando llama-server"
sh -c "$LLM_START_CMD"
started_llm=1

waited=0
until curl -fsS "$LLM_URL/models" >/dev/null; do
  waited=$((waited + 2))
  if [ "$waited" -ge "$LLM_WAIT_SECONDS" ]; then
    echo "llama-server no respondió en $LLM_URL/models" >&2
    exit 1
  fi
  sleep 2
done
echo "$(date -Is) modelo listo; generando conjuntos"

cd "$BACKEND"
# AI_TEXT_ENABLED=true solo en este proceso. El API de día sigue en false.
AI_TEXT_ENABLED=true \
AI_BASE_URL="$LLM_URL" \
AI_API_KEY="${AI_API_KEY:-not-needed}" \
  "$PYTHON" -m app.jobs.nightly_outfits

echo "$(date -Is) lote terminado; restaurando servicios"
sh -c "$LLM_STOP_CMD"
started_llm=0
sh -c "$ARMARIO_START_CMD"
stopped_armario=0
trap - EXIT
echo "$(date -Is) armario de nuevo en marcha"
