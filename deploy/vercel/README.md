# Frontend en Vercel

El proyecto de Vercel usa este repo. No hace falta desplegar desde aquí: con la configuración de abajo el proyecto queda listo para importarlo.

## Proyecto

| Ajuste | Valor |
| --- | --- |
| Root Directory | `frontend` |
| Framework | Next.js (también está en `frontend/vercel.json`) |
| Install | `npm install` |
| Build | `npm run build` |
| Output | el de Next.js. No uses `output: 'standalone'` como requisito de Vercel; el `next.config.js` lo deja por la imagen Docker y Vercel lo ignora. |
| Node | 20 |

`app/api/v1/[...path]/route.ts` reenvía `/api/v1` al teléfono usando `BACKEND_URL` en tiempo de petición. `maxDuration` está en 60 s. El plan de Vercel puede cortar antes; de día las sugerencias no deberían esperar al modelo.

Las fotos pasan por ese proxy y Vercel limita el cuerpo (4,5 MB en el plan Hobby). Si una subida grande falla, el navegador puede llamar al Funnel directamente con `NEXT_PUBLIC_API_URL` (el cliente ya lo usa cuando está definido) y hay que tener ese origen en `CORS_ORIGINS` del API.

## Variables

Definirlas en Production y Preview. No pongas `service_role` ni `SUPABASE_JWT_SECRET` aquí.

| Variable | Valor |
| --- | --- |
| `NEXT_PUBLIC_SUPABASE_URL` | `https://jvuzcuntgfmcjrrbsmda.supabase.co` |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | clave anon o publishable del mismo proyecto (la misma que entrenador) |
| `NEXT_PUBLIC_SUPABASE_OAUTH_PROVIDERS` | opcional, por ejemplo `google,github` |
| `NEXT_PUBLIC_API_URL` | `https://<telefono>.<tailnet>.ts.net` (sin barra final) |
| `BACKEND_URL` | la misma URL del Funnel, para el proxy de `/api/v1` |
| `NEXTAUTH_SECRET` | solo si aún usas el login local de NextAuth; en Vercel no actives `DEV_MODE` |

`NODE_ENV=production` en Vercel. El login de desarrollo no se muestra aunque alguien ponga `DEV_MODE=true`.

En el teléfono, `CORS_ORIGINS` debe incluir el dominio de Vercel (`https://<proyecto>.vercel.app` y el dominio propio si lo hay) y `APP_URL` debe ser esa misma URL para los enlaces de las notificaciones.

## Supabase Auth

En el proyecto `jvuzcuntgfmcjrrbsmda`, Authentication → URL configuration:

- Site URL: `https://<tu-app>.vercel.app`
- Redirect URLs:
  - `https://<tu-app>.vercel.app/auth/callback`
  - `http://localhost:3000/auth/callback` (pruebas locales)

El frontend inicia sesión con `@supabase/ssr` (correo y contraseña, enlace mágico y, si las listas, Google o GitHub). El access token de Supabase viaja en `Authorization` hacia el API. El API lo verifica con el JWKS (`/auth/v1/.well-known/jwks.json`, ES256/RS256) o, si el proyecto aún firma en HS256, con `SUPABASE_JWT_SECRET` en el teléfono. El `sub` y el email del token crean el usuario de Armario en el primer acceso. Peticiones sin token reciben 401. El token anónimo y el `service_role` no sirven.

El login de desarrollo (`DEBUG=true` y sin `SUPABASE_URL`) sigue valiendo solo en local. Con Supabase configurado, `DEBUG=true` no abre ese login.
