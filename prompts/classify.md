# Prompt de clasificación por estilo

Este es el prompt que usa `ytmsplitter ai` (implementado en `ytmsplitter/ai.py`).
Lo dejo aquí para que puedas clasificar a mano o con tu asistente favorito sin
gastar una API.

## Sistema

```
Clasificas canciones por estilo. Usas tu conocimiento del mundo sobre el artista
y el tema, no solo el texto. Respondes SOLO con un objeto JSON que mapea
videoId -> etiqueta.
```

## Taxonomía (etiqueta CERRADA, una sola por canción)

| Etiqueta | Cubre |
|---|---|
| `game_ost` | Videojuegos: bandas sonoras, VGM, chiptune, remixes de juegos |
| `film_tv_ost` | Bandas sonoras de cine, series o documentales |
| `anime_jp` | Anime (OP/ED), J-pop, J-rock, city pop japonés, música japonesa |
| `chillhop_lofi` | Lo-fi, chillhop, hip hop instrumental relajado, edits tipo AMV, wave |
| `rap_hiphop` | Rap, hip hop, boom bap, trap, drill (con voces) |
| `rock_metal` | Rock, metal, punk, grunge, nu-metal, hard rock |
| `indie_alt` | Indie, alternativo, bedroom pop, psicodelia, shoegaze, noise, math |
| `electronic_dance` | EDM, house, techno, drum&bass, synthwave, electro |
| `phonk` | Phonk, drift phonk |
| `hardcore_experimental` | Breakcore, hardcore, industrial, noise, experimental |
| `rnb_soul_funk` | R&B, soul, funk, disco, groove |
| `jazz` | Jazz, jazz-funk, bossa, swing |
| `pop` | Pop mainstream y clásicos pop |
| `latin_spanish` | Música en español o latina (cualquier género) |
| `ambient_relax` | Ambient, drone, new age, relax/zen/dormir |
| `classical_orchestral` | Clásica, orquestal, piano solo |
| `meme_internet` | Música de internet/meme/weird/shonk |
| `other` | No encaja en ninguna |

## Reglas

- Si es OST de un juego → `game_ost`, aunque sea electrónico.
- Canciones de anime → `anime_jp`.
- Instrumental de hip hop relajado → `chillhop_lofi`; con rap cantado → `rap_hiphop`.
- Si dudas entre dos, elige la que describa mejor el **uso/vibe** de la canción.
- Responde **solo** con el JSON `{videoId: etiqueta}`, sin markdown.

## Entrada / salida

Entrada: líneas `videoId :: Título — Artista(s) || album: Álbum`.
Salida: `{ "videoId": "etiqueta", ... }` → guarda el resultado como
`data/ai_labels.json` y ejecuta `ytmsplitter ai --create`.
