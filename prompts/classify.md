# Prompt: style classification

This is the prompt used by `ytmsplitter ai` (implemented in `ytmsplitter/ai.py`).
It is kept here so you can classify songs manually or with your favourite
assistant without spending API credits.

## System

```text
You classify songs by style. Use your world knowledge about the artist and the
track, not just the text. Reply with ONLY a JSON object mapping videoId -> label.
```

## Taxonomy (closed set, exactly one label per song)

| Label | Covers |
|---|---|
| `game_ost` | Video games: soundtracks, VGM, chiptune, game remixes |
| `film_tv_ost` | Film, TV series and documentary soundtracks |
| `anime_jp` | Anime (OP/ED), J-pop, J-rock, Japanese city pop, Japanese music |
| `chillhop_lofi` | Lo-fi, chillhop, relaxed instrumental hip hop, AMV-style edits, wave |
| `rap_hiphop` | Rap, hip hop, boom bap, trap, drill (with vocals) |
| `rock_metal` | Rock, metal, punk, grunge, nu-metal, hard rock |
| `indie_alt` | Indie, alternative, bedroom pop, psychedelia, shoegaze, noise, math |
| `electronic_dance` | EDM, house, techno, drum & bass, synthwave, electro |
| `phonk` | Phonk, drift phonk |
| `hardcore_experimental` | Breakcore, hardcore, industrial, noise, experimental |
| `rnb_soul_funk` | R&B, soul, funk, disco, groove |
| `jazz` | Jazz, jazz-funk, bossa nova, swing |
| `pop` | Mainstream pop and pop classics |
| `latin_spanish` | Music in Spanish or Latin music (any genre) |
| `ambient_relax` | Ambient, drone, new age, relaxation/zen/sleep |
| `classical_orchestral` | Classical, orchestral, solo piano |
| `meme_internet` | Internet/meme/weird/shonk music |
| `other` | None of the above |

## Rules

- A game soundtrack is `game_ost`, even if it is electronic.
- Anime songs are `anime_jp`.
- Relaxed instrumental hip hop is `chillhop_lofi`; hip hop with rapped vocals is
  `rap_hiphop`.
- When in doubt, choose the label that best describes how the song is used.
- Reply with **only** the JSON `{videoId: label}`, without markdown.

## Input / output

Input: lines in the form `videoId :: Title — Artist(s) || album: Album`.

Output: `{ "videoId": "label", ... }` → save it as `data/ai_labels.json` and run
`ytmsplitter ai --create`.
