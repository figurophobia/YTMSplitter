<div align="center">

# 🎧 YTMSplitter

**Divide tu playlist «Me gusta» de YouTube Music en playlists que de verdad se distinguen.**

¿Tienes 700 canciones de 30 rollos distintos en un mismo cajón? YTMSplitter las
clasifica por estilo y te monta las playlists por ti.

[![License: MIT](https://img.shields.io/badge/License-MIT-6f42c1.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB.svg)](https://www.python.org/)
[![ytmusicapi](https://img.shields.io/badge/powered%20by-ytmusicapi-ff0000.svg)](https://github.com/sigma67/ytmusicapi)

</div>

```text
                       ┌──────────────────────────┐
   «Me gusta»  ──────► │         YTMSplitter       │ ──────►  playlists por estilo
   722 canciones       └──────────────────────────┘
                       chips nativos  ·  clasificación con IA
```

---

## ✨ Qué hace

Coge toda tu playlist **Me gusta** y la abre en varias playlists temáticas. Tiene
dos motores, y puedes usar el que prefieras (o los dos):

| Motor | Cómo clasifica | Resultado |
|---|---|---|
| 🟥 **`chips`** | Usa los *chips* (mood/género) que **YouTube Music ya calcula** sobre tu lista | ~15 playlists tipo *Chill*, *Rock*, *Hip-hop*… |
| 🤖 **`ai`** | Un **LLM** etiqueta cada canción con un estilo fino y luego se agrupan | **< 10 playlists** con sentido: *Videojuegos*, *Cine/series/anime*, *Chillhop & Lo-fi*… |

El motor `ai` es el interesante: distingue cosas que los géneros genéricos no,
como **bandas sonoras de videojuegos** frente a **de cine**, o **chillhop tipo AMV**
frente a **rap**.

---

## 🚀 Instalación

```bash
git clone https://github.com/figurophobia/YTMSplitter
cd YTMSplitter

python -m venv .venv && source .venv/bin/activate
pip install -e ".[firefox]"     # incluye lectura de cookies de Firefox
```

Sin el extra `firefox` también funciona: puedes pegar tus cabeceras a mano.

---

## 🧭 Uso rápido

```bash
# 1. Sesión (lee las cookies de tu Firefox, no hace falta copiar nada)
ytmsplitter auth

# 2. Descarga tus «Me gusta»
ytmsplitter export

# 3. Divide con IA y crea las playlists
AI_API_KEY=sk-... AI_MODEL=gpt-4o-mini ytmsplitter ai --create
```

…o con los chips nativos de YouTube Music (sin clave de IA):

```bash
ytmsplitter chips --create
```

Comprueba el estado cuando quieras:

```bash
ytmsplitter doctor
```

---

## 📚 Comandos

| Comando | Para qué |
|---|---|
| `ytmsplitter auth` | Configura/renueva la sesión (Firefox por defecto, o `--headers fichero`) |
| `ytmsplitter doctor` | Diagnóstico: sesión, canciones, etiquetas y playlists creadas |
| `ytmsplitter export` | Descarga tu playlist «Me gusta» a `data/liked.json` |
| `ytmsplitter chips` | Clasifica con los chips nativos (añade `--create` para crear) |
| `ytmsplitter ai` | Clasifica con IA y agrupa (añade `--create` para crear) |

Banderas útiles de `chips` y `ai`:

```text
--create              crea las playlists (por defecto solo informa)
--dry-run             muestra qué haría, sin tocar tu cuenta
--privacy             PRIVATE (defecto) | UNLISTED | PUBLIC
--uncovered           (chips) añade una playlist con las canciones sin clasificar
--delete-old-chips    (ai) borra antes las playlists «Me gusta · …»
```

Todo es **idempotente**: se guarda qué playlist se creó y no se duplica al
re-ejecutar.

---

## 🤖 El motor de IA por dentro

1. Un LLM recibe `título + artistas + álbum` de cada canción y devuelve **un
   estilo fino** de una lista de 18 (ver `ytmsplitter/config.py` → `AI_TAGS`):
   `game_ost`, `film_tv_ost`, `anime_jp`, `chillhop_lofi`, `rap_hiphop`,
   `rock_metal`, `indie_alt`, `electronic_dance`, `phonk`, …
2. Esas etiquetas se agrupan en **menos de 10 playlists** (`AI_BUCKETS`).

Lo bueno: la agrupación es **configuración**, no código. Si quieres otras
playlists, edita `AI_BUCKETS` y re-ejecuta — no hay que volver a clasificar:

```bash
ytmsplitter ai --create --delete-old-chips
```

### Cualquier LLM compatible con OpenAI

```bash
export AI_BASE_URL=https://openrouter.ai/api/v1   # o Groq, Together, vLLM…
export AI_API_KEY=...
export AI_MODEL=anthropic/claude-3.5-sonnet
ytmsplitter ai --create
```

¿Sin ganas de pagar una API? También puedes clasificar tú mismo (o con tu asistente
favorito) usando `prompts/classify.md` y guardar el resultado como
`data/ai_labels.json`; luego `ytmsplitter ai --create` lo agrupa igual.

---

## 🔐 Sesión

YTMSplitter habla con YouTube Music a través de [`ytmusicapi`](https://github.com/sigma67/ytmusicapi),
que se autentica con **tus cookies**. Dos formas:

- **Firefox** (recomendado): `ytmsplitter auth` lee las cookies de tu perfil.
  Nota: las cookies de navegador **caducan a menudo**; si algo falla, repite este
  comando y listo.
- **A mano**: copia las cabeceras de una petición a `music.youtube.com`
  (DevTools → Network → clic derecho en una petición `browse`/`next` → *Copy* →
  *Copy request headers*), guárdalas en un fichero y usa
  `ytmsplitter auth --headers fichero`.

`data/auth.json` y las cabeceras contienen tu sesión: están en `.gitignore` y se
guardan con permisos `600`. **No los compartas.**

---

## 🧪 Ejemplo de salida

```console
$ ytmsplitter ai --create
• Clasificando con IA (gpt-4o-mini en https://api.openai.com/v1)…
  lote 1/10 (80 canciones)
  …
✓ etiquetadas 800/800

• 9 playlists, 800 asignaciones sobre 800 canciones
   168  Chillhop & Lo-fi
   141  Indie & Alternativo
   120  Rock & Metal
    86  Pop, Soul & Jazz
    71  Videojuegos
    54  Rap & Hip-hop
    48  Electrónica, ambiente y memes
    45  En español
    43  Cine, series y anime

• Playlists (creando)
  ✓ IA · Videojuegos: 71 canciones → PLxxxxxxxxxxxx
  ✓ IA · Cine, series y anime: 43 canciones → PLxxxxxxxxxxxx
  …
```

---

## 📁 Salida

```text
data/
  liked.json            todas tus canciones «me gusta»
  chips.json            chips detectados (mood/género)
  by_chip/<label>.json  canciones de cada chip
  ai_labels.json        estilo fino asignado por la IA a cada canción
  ai_buckets.json       agrupación final (etiquetas → playlists)
  created_*.json        qué playlists se crearon (idempotencia)
```

---

## ⚠️ Aviso

Proyecto **no oficial**, sin relación con Google ni YouTube. Usa la API interna
de YouTube Music mediante `ytmusicapi`; puede dejar de funcionar si cambian sus
endpoints. Úsalo bajo tu responsabilidad y respetando los términos de servicio
de YouTube.

## 📄 Licencia

[MIT](LICENSE) © 2026 David Sánchez Míguez
