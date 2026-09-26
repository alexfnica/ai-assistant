import argparse
from pathlib import Path
from .storage import Store
from .core import Core


def build_library(args):
    from .config import load_config
    from .documents import DocumentLibrary
    config = load_config(args.data_dir)
    return DocumentLibrary(config["docs_dir"], config["docs_exclude_sheets"]) if config["docs_dir"] else None


def build_music(args):
    import os
    import webbrowser
    from .spotify import Spotify
    from .youtube import YouTube
    launcher = getattr(os, "startfile", None)
    ui_search = None
    if launcher:      # Windows only
        from .spotify_ui import search_in_app
        ui_search = search_in_app
    return Spotify(args.data_dir, args.port, launcher=launcher, ui_search=ui_search), YouTube(args.data_dir, args.port), webbrowser.open


def build_model(store, args, library=None, youtube=None):
    """Cloud model with read-only tools first; the local model remains the offline fallback."""
    from .local_model import LocalModel
    from .cloud_model import CloudModel, HybridModel
    from .config import load_config, load_api_key
    from .tools import Toolbox
    local = LocalModel(store)
    local.warm()
    config = load_config(args.data_dir)
    if args.no_cloud or not config["cloud_enabled"]:
        return local
    cloud = CloudModel(store, Toolbox(store, library, youtube), load_api_key(args.data_dir), config, args.data_dir)
    return HybridModel(cloud, local)


def main():
    parser = argparse.ArgumentParser(description="JARVIS AFNICA v1 — desktop local")
    parser.add_argument("--data-dir", type=Path, default=Path(__file__).resolve().parent.parent / "data")
    parser.add_argument("--cli", action="store_true", help="Chat în terminal, fără interfață grafică")
    parser.add_argument("--holo", action="store_true", help="Interfața HOLO în browser, local")
    parser.add_argument("--port", type=int, default=4891)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--no-voice", action="store_true")
    parser.add_argument("--no-llm", action="store_true", help="Use explicit commands only")
    parser.add_argument("--no-cloud", action="store_true", help="Use only the local model")
    args = parser.parse_args()
    store = Store(args.data_dir / "jarvis.sqlite3")
    from .integrations import Integrations
    from .local_model import LocalModel
    from .config import load_config
    library = build_library(args)
    spotify, youtube, open_url = build_music(args)
    model = None if args.no_llm else build_model(store, args, library, youtube)
    core = Core(store, Integrations(llm=model, docs=library, spotify=spotify, youtube=youtube, open_url=open_url, open_app=getattr(__import__('os'), 'startfile', None), aquarium_path=load_config(args.data_dir).get('aquarium_path', '')))
    if args.holo:
        from .holo_server import run
        run(store, args.port, not args.no_browser, not args.no_voice, core=core)
    elif args.cli:
        print("JARVIS AFNICA v1 | ajutor = comenzi | exit = închidere")
        print("CLI: fără alerte automate; vezi termenele cu «task-uri toate».")
        while True:
            try:
                text = input("Tu > ")
                if text.strip().lower() in ("exit", "quit"):
                    break
                print("Jarvis >", core.handle(text).text)
            except (EOFError, KeyboardInterrupt):
                break
            except ValueError as error:
                print(error)
    else:
        from .desktop import run
        run(core)
    if model:
        model.close()


if __name__ == "__main__":
    main()
