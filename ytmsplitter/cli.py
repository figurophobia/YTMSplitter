"""Interfaz de línea de comandos de YTMSplitter."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import config as C
from . import api, auth, ai

OK, BAD, ARROW, DOT = "✓", "✗", "→", "•"


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _load_liked(auto_export: bool = True) -> list[dict]:
    liked = api.load_json(C.LIKED_FILE)
    if liked:
        return liked
    if not auto_export:
        raise SystemExit(f"Falta {C.LIKED_FILE}. Ejecuta antes: ytmsplitter export")
    print(f"{DOT} No hay {C.LIKED_FILE.relative_to(Path.cwd()) if C.LIKED_FILE.is_relative_to(Path.cwd()) else C.LIKED_FILE}, descargando…")
    return cmd_export(argparse.Namespace())


def _privacy(value: str) -> str:
    return value.upper()


def _create_or_skip(args, created: dict, key: str, title: str,
                    video_ids: list[str], dry_run: bool, privacy: str,
                    created_file: Path) -> None:
    if not video_ids:
        print(f"  {DOT} {title}: sin canciones, se omite")
        return
    if dry_run:
        state = "ya creada" if key in created else "nueva"
        print(f"  {DOT} {title}: {len(video_ids)} canciones ({state})")
        return
    if key in created:
        print(f"  {OK} {title}: ya existe, se omite")
        return
    yt = api.client()
    pid = api.create_playlist(yt, title, video_ids, privacy=privacy)
    created[key] = pid
    api.save_json(created_file, created)
    print(f"  {OK} {title}: {len(video_ids)} canciones → {pid}")


# --------------------------------------------------------------------------- #
# Comandos
# --------------------------------------------------------------------------- #
def cmd_auth(args) -> int:
    if args.headers:
        raw = Path(args.headers).read_text(encoding="utf-8")
        path = auth.setup_from_headers(raw)
        print(f"{OK} auth.json generado a partir de {args.headers}")
    else:
        path = auth.setup_from_firefox()
        print(f"{OK} auth.json regenerado desde Firefox")

    yt = api.client(path)
    if api.is_authenticated(yt):
        print(f"{OK} sesión autenticada")
        return 0
    print(f"{BAD} la sesión NO autentica (logged_in=0). Prueba a pegar cabeceras frescas.")
    return 1


def cmd_doctor(args) -> int:
    print(f"YTMSplitter {__import__('ytmsplitter').__version__}")
    print(f"directorio de datos: {C.DATA_DIR}")

    print(f"\n{DOT} Sesión")
    print(f"  auth.json: {OK if C.AUTH_FILE.exists() else BAD}")
    if C.AUTH_FILE.exists():
        print(f"  autenticada: {OK if api.is_authenticated(api.client()) else BAD}")

    print(f"\n{DOT} Datos")
    liked = api.load_json(C.LIKED_FILE)
    labels = api.load_json(C.LABELS_FILE)
    print(f"  canciones descargadas: {len(liked) if liked else 0}")
    print(f"  etiquetas IA:          {len(labels) if labels else 0}")

    if C.CREATED_AI_FILE.exists() or C.CREATED_CHIPS_FILE.exists():
        print(f"\n{DOT} Playlists creadas")
        for f, label in ((C.CREATED_AI_FILE, "IA"), (C.CREATED_CHIPS_FILE, "chips")):
            created = api.load_json(f, {})
            print(f"  {label}: {len(created)}")
    return 0


def cmd_export(args) -> list[dict]:
    yt = api.client()
    api.require_auth(yt)
    print(f"{DOT} Descargando tu playlist «Me gusta»…")
    tracks, total = api.get_liked_tracks(yt)
    api.save_json(C.LIKED_FILE, tracks)
    print(f"{OK} {len(tracks)} canciones → {C.LIKED_FILE} (YT Music dice {total})")
    return tracks


def cmd_chips(args) -> int:
    yt = api.client()
    api.require_auth(yt)
    liked = _load_liked()
    liked_ids = [t["videoId"] for t in liked]

    chips = api.get_chips(yt)
    if not chips:
        print(f"{BAD} no se han encontrado chips en la página de Me gusta")
        return 1
    print(f"{DOT} {len(chips)} chips encontrados")
    for c in chips:
        c["kind"] = ("mood" if c["label"] in C.MOODS
                     else "genre" if c["label"] in C.GENRES else "otro")
    api.save_json(C.CHIPS_FILE, chips)

    by_chip: dict[str, list[str]] = {}
    for i, c in enumerate(chips, 1):
        items = api.fetch_chip_songs(yt, c["token"])
        vids = list(dict.fromkeys(it["videoId"] for it in items if it.get("videoId")))
        by_chip[c["label"]] = vids
        api.save_json(C.BY_CHIP_DIR / f"{c['label']}.json", vids)
        print(f"  [{i:2d}/{len(chips)}] {c['label']:26s} {len(vids):4d}")

    covered = set().union(*map(set, by_chip.values())) if by_chip else set()
    uncovered = [v for v in liked_ids if v not in covered]
    api.save_json(C.SUMMARY_FILE, {
        "liked_total": len(liked_ids), "covered": len(covered),
        "uncovered": len(uncovered), "by_chip": {k: len(v) for k, v in by_chip.items()},
    })
    api.save_json(C.UNCOVERED_FILE, uncovered)
    print(f"{OK} cubiertas por algún chip: {len(covered)}/{len(liked_ids)} "
          f"(sin chip: {len(uncovered)})")

    if not args.create:
        print(f"{ARROW} añade --create para crear las playlists")
        return 0

    print(f"\n{DOT} Playlists ({'simulación' if args.dry_run else 'creando'})")
    created = api.load_json(C.CREATED_CHIPS_FILE, {})
    for label, vids in by_chip.items():
        title = C.CHIPS_PREFIX + C.PLAYLIST_NAMES.get(label, label)
        _create_or_skip(args, created, label, title, vids, args.dry_run, args.privacy,
                        C.CREATED_CHIPS_FILE)
    if args.uncovered:
        title = C.CHIPS_PREFIX + "Sin clasificar"
        _create_or_skip(args, created, "__uncovered__", title, uncovered, args.dry_run,
                        args.privacy, C.CREATED_CHIPS_FILE)
    if args.dry_run:
        print(f"{ARROW} vuelve a ejecutar sin --dry-run para crear de verdad")
    return 0


def cmd_ai(args) -> int:
    liked = _load_liked()

    labels = api.load_json(C.LABELS_FILE, {})
    missing = [t["videoId"] for t in liked if t["videoId"] not in labels]
    if missing:
        base_url = args.base_url or C.AI_BASE_URL
        api_key = args.api_key or C.AI_API_KEY
        model = args.model or C.AI_MODEL
        if not api_key or not model:
            print(f"{BAD} faltan {len(missing)} canciones por etiquetar y no hay clave de IA.")
            print("  Define AI_API_KEY y AI_MODEL (y opcional AI_BASE_URL), o:")
            print("    AI_API_KEY=… AI_MODEL=gpt-4o-mini ytmsplitter ai --create")
            print("  También puedes reutilizar data/ai_labels.json ya existente.")
            return 2
        print(f"{DOT} Clasificando con IA ({model} en {base_url})…")
        labels.update(ai.classify_all(liked, base_url, api_key, model))
        api.save_json(C.LABELS_FILE, labels)
        print(f"{OK} etiquetadas {len(labels)}/{len(liked)}")

    buckets = ai.build_buckets(labels)
    api.save_json(C.BUCKETS_FILE, buckets)
    total = sum(len(v) for v in buckets.values())
    print(f"\n{DOT} {len(buckets)} playlists, {total} asignaciones sobre {len(labels)} canciones")
    for name, vids in buckets.items():
        print(f"  {len(vids):4d}  {name}")

    if not args.create:
        print(f"\n{ARROW} añade --create para crear las playlists")
        return 0

    print(f"\n{DOT} Playlists ({'simulación' if args.dry_run else 'creando'})")
    created = api.load_json(C.CREATED_AI_FILE, {})

    if args.delete_old_chips and not args.dry_run:
        for title in api.delete_playlists_with_prefix(api.client(), C.CHIPS_PREFIX):
            print(f"  {DOT} borrada {title}")

    for name, vids in buckets.items():
        _create_or_skip(args, created, name, C.AI_PREFIX + name, vids, args.dry_run,
                        args.privacy, C.CREATED_AI_FILE)
    if args.dry_run:
        print(f"{ARROW} vuelve a ejecutar sin --dry-run para crear de verdad")
    return 0


# --------------------------------------------------------------------------- #
# Parser
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ytmsplitter",
        description="Divide tu «Me gusta» de YouTube Music en playlists por estilo.",
    )
    p.add_argument("--version", action="version", version="%(prog)s 1.0.0")
    sub = p.add_subparsers(dest="command", required=True)

    a = sub.add_parser("auth", help="configura la sesión (cookies de Firefox o cabeceras)")
    a.add_argument("--headers", metavar="FICHERO",
                   help="fichero con cabeceras copiadas del navegador (por defecto: Firefox)")
    a.set_defaults(func=cmd_auth)

    d = sub.add_parser("doctor", help="diagnóstico de sesión y datos")
    d.set_defaults(func=cmd_doctor)

    e = sub.add_parser("export", help="descarga tu playlist «Me gusta»")
    e.set_defaults(func=cmd_export)

    def add_create_flags(sp, with_delete=False):
        sp.add_argument("--create", action="store_true", help="crea las playlists")
        sp.add_argument("--dry-run", action="store_true", help="no crea nada, solo informa")
        sp.add_argument("--privacy", default="PRIVATE",
                        choices=["PRIVATE", "UNLISTED", "PUBLIC"])
        if with_delete:
            sp.add_argument("--delete-old-chips", action="store_true",
                            help="borra las playlists 'Me gusta · …' antes de crear")

    c = sub.add_parser("chips", help="clasifica con los chips nativos de YT Music")
    add_create_flags(c)
    c.add_argument("--uncovered", action="store_true",
                   help="añade una playlist con las canciones sin chip")
    c.set_defaults(func=cmd_chips)

    i = sub.add_parser("ai", help="clasifica con un LLM y agrupa en pocas playlists")
    add_create_flags(i, with_delete=True)
    i.add_argument("--model", help="modelo (por defecto AI_MODEL)")
    i.add_argument("--base-url", help="endpoint compatible con OpenAI (por defecto AI_BASE_URL)")
    i.add_argument("--api-key", help="clave de API (por defecto AI_API_KEY)")
    i.set_defaults(func=cmd_ai)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = args.func(args)
    except api.AuthError as e:
        print(f"{BAD} {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\ninterrumpido")
        return 130
    return 0 if isinstance(result, list) else (result or 0)


if __name__ == "__main__":
    raise SystemExit(main())
