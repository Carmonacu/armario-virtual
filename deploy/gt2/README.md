# Armario en el Realme GT 2

El API, Redis y el worker de arq corren **sin Docker** dentro de Ubuntu en proot (Termux), en el GT 2 (aarch64, 8 GB). El frontend no va en el teléfono: va en Vercel. Ver `deploy/vercel/README.md`.

La base de datos ya está en Supabase Postgres, proyecto `jvuzcuntgfmcjrrbsmda`, esquema `armario`, rol `armario_app` (search_path=`armario`), pooler de sesión `aws-0-eu-west-1`. La URL es asyncpg con `?ssl=require`. No hace falta Postgres en el teléfono y las migraciones no tocan otros esquemas.

rembg y el image-worker **no se instalan**. De día el teléfono no tiene modelo de visión.

## 1. Instalar

Dentro de proot Ubuntu, con el repo clonado:

```sh
export ARMARIO_ROOT="$HOME/armario-virtual"
cp "$ARMARIO_ROOT/deploy/gt2/env.example" "$HOME/armario.env"
# Edita SECRET_KEY y DATABASE_URL. DEBUG debe seguir en false.
sh "$ARMARIO_ROOT/deploy/gt2/install.sh"
```

`install.sh` crea el venv en `~/.venv/armario`, instala `backend/requirements.txt` (sin `requirements-extras.txt`) y lanza `alembic upgrade head` contra el esquema `armario`.

Redis puede venir de `apt install redis-server` dentro de proot, o del Redis de Termux si proot comparte la red. En ese caso no actives el servicio runit de Redis y apunta `REDIS_URL` a `redis://127.0.0.1:6379/0`.

## 2. Servicios runit

Copia cada carpeta de `deploy/gt2/runit/` a tu directorio de servicios (en proot suele ser `/etc/service`, en Termux `$PREFIX/var/service`) y dale permiso de ejecución a `run`:

```sh
chmod +x deploy/gt2/runit/*/run
mkdir -p /etc/service
cp -a deploy/gt2/runit/redis /etc/service/redis
cp -a deploy/gt2/runit/armario-api /etc/service/armario-api
cp -a deploy/gt2/runit/armario-worker /etc/service/armario-worker
```

Variables que leen los scripts si no quieres editarlos:

| Variable | Defecto |
| --- | --- |
| `ARMARIO_ROOT` | `$HOME/armario-virtual` |
| `ARMARIO_VENV` | `$HOME/.venv/armario` |
| `ARMARIO_ENV` | `$HOME/armario.env` |
| `ARMARIO_PORT` | `8000` |

El API escucha en `0.0.0.0` para que Tailscale, que corre en Termux, llegue al puerto. `DEBUG=false`, `AI_TEXT_ENABLED=false` y `AI_VISION_ENABLED=false` se fuerzan en el servicio: el login de desarrollo no está disponible y el API no intenta hablar con el modelo de día.

No hay servicio para el image-worker.

## 3. Tailscale Funnel

En Termux (donde está Tailscale), con el API ya escuchando en el puerto 8000:

```sh
tailscale funnel --bg 8000
tailscale funnel status
```

La URL pública es `https://<nombre>.<tailnet>.ts.net`. Esa URL es `BACKEND_URL` / `NEXT_PUBLIC_API_URL` en Vercel y un origen de `CORS_ORIGINS`. `TRUSTED_PROXY_COUNT=1` porque Funnel añade `X-Forwarded-For`.

## 4. Noche: conjuntos para el día siguiente

`deploy/gt2/nightly.sh` hace esto:

1. Para los servicios de Armario (`ARMARIO_STOP_CMD`, por defecto `mode stop armario`).
2. Arranca llama-server (`LLM_START_CMD`, por defecto `mode start llm`).
3. Espera a que `GET $LLM_URL/models` responda (`LLM_URL` por defecto `http://127.0.0.1:8080/v1`, así que llama a `/v1/models`).
4. Ejecuta `python -m app.jobs.nightly_outfits` con `AI_TEXT_ENABLED=true` solo en ese proceso.
5. Para el modelo y vuelve a arrancar Armario.

El script `~/bin/mode` no está en este repo. Si tus subcomandos son otros, exporta los cuatro comandos completos:

```sh
export ARMARIO_STOP_CMD='mode armario off'
export ARMARIO_START_CMD='mode armario on'
export LLM_START_CMD='mode llm on'
export LLM_STOP_CMD='mode llm off'
```

Cron (hora local, antes de medianoche para que el objetivo sea «mañana»):

```cron
0 23 * * * /bin/sh $HOME/armario-virtual/deploy/gt2/nightly.sh >>$HOME/armario-nightly.log 2>&1
```

Si el cron corre ya de madrugada, añade el argumento editando la línea del `python` o lanza a mano:

```sh
cd "$ARMARIO_ROOT/backend"
AI_TEXT_ENABLED=true "$HOME/.venv/armario/bin/python" -m app.jobs.nightly_outfits --for-today
```

Opciones: `--date YYYY-MM-DD`, `--user <uuid>`, `--count 3`, `--force` (marca como omitidos los conjuntos pendientes de esa fecha y genera otros).

Para cada usuario activo con ubicación guarda hasta 3 conjuntos (`source=scheduled`) usando el tiempo previsto de ese día y la ocasión por defecto de sus preferencias. Quien no tenga ubicación o no tenga bastante ropa se omite; un fallo no para al resto.

Por la mañana la app enseña esos conjuntos sin llamar a la IA. Si de día pides uno nuevo, el API responde con los ya preparados y la interfaz explica, en español, que el asistente está apagado. Si no hay ninguno, el mensaje dice que hay que esperar a la pasada nocturna.

### Descripciones de prendas

El modelo de la noche es solo texto y no puede etiquetar fotos. Las prendas que siguen en `tagging_status=pending` se quedan en cola. El lote escribe en el log cuántas hay. Solo si en ese proceso `AI_VISION_ENABLED=true` (un endpoint de visión de verdad, no llama-server) las encola en arq para analizarlas en la misma ventana. Con la configuración de este teléfono no se encolan.
