import contextlib
import getpass
import logging
import os
import socket
import time
import uuid
import zipfile
from argparse import ArgumentParser
from typing import Optional

import questionary
import requests
import termcolor
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse

config = {
    "show_ignore": False
}

def ignoring(c: str):
    if not config['show_ignore']:
        return

    print(termcolor.colored(f"! ignoring  {c}", attrs=['dark']))

def zip_files(folder_path, zip_path, packignore: dict[str, list[Optional[str]]]):
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(folder_path, topdown=True):
            if (any(root.startswith(folder_path + dir) for dir in packignore['dirs'])) \
            or (any(item in root.split('/') for item in packignore['any_pos_dirs'])):
                ignoring(root)
                continue

            for file in files:
                file_path = os.path.join(root, file)
                if file_path == (folder_path + zip_path):
                    continue

                if (file in packignore['top_dir_files'] and root == folder_path)\
                or (file_path in packignore['full_dir_files'])\
                or (file in packignore['any_dir_files']):
                    ignoring(file_path)
                    continue

                print(termcolor.colored('packnow ', 'green') + file_path)
                zipf.write(file_path, os.path.relpath(file_path, folder_path))

def make_parser() -> ArgumentParser:
    parser = ArgumentParser()
    parser.add_argument(
        "-d",
        "--dir",
        dest="dir",
        help="The directory to pack.",
        default="./",
        type=str
    )
    parser.add_argument(
        "-n",
        "--name",
        dest="name",
        help="Specify a custom name for your zipped file instead of 'packnow' (without the extension)",
        type=str,
        default="packnow"
    )
    parser.add_argument(
        "--show-ignore", 
        dest="show_ignore", 
        help="Whether to show the ignored files or not.",
        type=bool,
        default=False
    )
    parser.add_argument(
        "--dangerously-disable-uuid",
        dest="disable_uuid",
        help="Dangerously disable the UUID feature."
             "\nWARNING: THIS COULD OVERWRITE EXISTING FILES",
        type=bool,
        default=False
    )
    subcmd = parser.add_subparsers(
        dest='subcmd', help='Subcommands. Default to `pack`', metavar='SUBCOMMAND', 
        required=False
    )
    hostcmd = subcmd.add_parser(
        'host',
        help="Host a simple server to send the ZIP file to another place"
    )
    hostcmd.add_argument(
        '--host',
        help="Specify the host. (e.g., 0.0.0.0)",
        type=str
    )
    hostcmd.add_argument(
        '--port',
        help="Specify the port. (e.g., 8080)",
        default=8080,
        type=int
    )
    hostcmd.add_argument(
        "--file",
        help="The zipped file. (required)",
        type=str,
        required=True,
        dest="file"
    )
    hostcmd.add_argument(
        "--password",
        dest="password",
        help="Set a password to restrict access. (optional)",
        type=str,
        default=""
    )
    
    getcmd = subcmd.add_parser(
        'get',
        help="Get a ZIP file from a server."
    )
    getcmd.add_argument(
        "--url",
        help="The URL to get.",
        required=True
    )
    return parser


def pack(args):
    if args.disable_uuid:
        print(
            termcolor.colored(
                "WARNING: " + \
                "By disabling the UUID feature, existing files may be overwritten.",
                "yellow"
            )
        )
        fn = args.name + ".zip"
    else:
        fn = f"{args.name}-" + str(uuid.uuid4()).split('-')[0] + ".zip"

    config['show_ignore'] = args.show_ignore

    try:
        packignore = questionary.select(
            "Select a packignore template",
            choices=["replit-python", "none"]
        ).ask()
        
        folder_path = args.dir

        print(termcolor.colored(
            f"... Packing into '{fn}'",
            attrs=['dark']
        ))

        start = time.time()
        zip_files(folder_path, fn, {
            "replit-python": {
                "dirs": [".config", "venv", ".upm", ".cache"],
                "any_pos_dirs": ["__pycache__"],
                "any_dir_files": [],
                "top_dir_files": [
                    "poetry.lock", 
                    "pyproject.toml", 
                    ".replit", 
                    "replit.nix", 
                    ".breakpoints"
                ],
                "full_dir_files": []
            },
            "none": {
                "dirs": [],
                "any_pos_dirs": [],
                "any_dir_files": [],
                "top_dir_files": [],
                "full_dir_files": []
            }
        }[packignore])
        print(f"\n✨ Done: {fn}")
        print(
            termcolor.colored(
                f"Zipped within {(time.time() - start):.2f}s",
                attrs=['dark']
            )
        )
        host_next = input("Would you like to host a server? (y/n) ")
        if host_next.lower() == 'y':
            # monkey patching
            args.host = "0.0.0.0"
            args.port = 8080
            args.file = fn
            args.password = getpass.getpass('Assign password (leave blank to ignore): ')

            host(args)

        exit(0)

    except Exception as error:
        with contextlib.suppress(FileNotFoundError):
            os.remove(fn)

        print(termcolor.colored("packnow ", "red") + "operation failed! (removed zip)")
        print(termcolor.colored(str(error), "red"))
        exit(1)

def host(args):
    if not args.file.endswith('.zip'):
        print(termcolor.colored("provided file was not a zipped file", "red"))
        exit(1)

    @contextlib.asynccontextmanager
    async def lifespan(_):
        if os.environ.get('REPL_SLUG'):
            url = f"https://{os.environ['REPL_SLUG']}.{os.environ['REPL_OWNER']}.repl.co"
        else:
            url = f"http://{socket.gethostbyname(socket.gethostname())}:{args.port}"

        print()
        print(termcolor.colored("packnow host ", "green") + "running at " + url)
        print(
            termcolor.colored(
                f"Try using\n\n  packnow get --url {url}\n\n...somewhere else to get this pack",
                attrs=['dark']
            )
        )
        yield
        print(
            termcolor.colored(
                "\nClosing uvicorn server...",
                'red'
            )
        )

    app = FastAPI(docs_url=None, redoc_url=None, lifespan=lifespan)

    @app.get('/')
    async def index():
        print(termcolor.colored('GET ', 'green') + '/')
        return JSONResponse({
            "requiresPassword": not not args.password # type: ignore
        })

    @app.get('/get')
    async def get(req: Request):
        if args.password:
            pwd = req.headers.get('Authorization')
            if pwd != args.password:
                print(termcolor.colored('GET pack (blocked) ', 'red') + 'invalid password')
                return JSONResponse({ "error": "password" }, 401)

        print(termcolor.colored('GET ', 'green') + 'pack (giving)')
        return FileResponse(args.file, filename="packnow.zip")

    uvicorn.run(app, host=args.host, port=args.port, log_level=logging.ERROR)

def receive(args):
    fn = "-".join(str(uuid.uuid4()).split('-')[:2]) + ".zip"

    res = requests.get(args.url)
    requires_pwd: bool = res.json()['requiresPassword']
    pwd = getpass.getpass("Enter password: ") if requires_pwd else ""

    actual_url = (args.url + 'get') if args.url.endswith('/') else (args.url + '/get')

    response = requests.get(
        actual_url, 
        stream=True,
        headers={
            "Authorization": pwd
        }
    )

    if response.status_code == 200:
        with open(fn, 'wb') as file:
            for chunk in response.iter_content(chunk_size=1024):
                print(termcolor.colored("! chunked 1024", attrs=['dark']))
                file.write(chunk)

        print(termcolor.colored('packnow ', 'green') + 'extracting...')
        extract_as: str = f"packnow-{time.time():.0f}"
        
        with zipfile.ZipFile(fn, 'r') as zip_ref:
            zip_ref.extractall(extract_as)

        print(termcolor.colored('packnow ', 'green') + f'extracted as {extract_as}')
        os.remove(fn)

        exit(0)

    else:
        if requires_pwd:
            print(termcolor.colored('invalid password', 'red'))
        else:
            print(termcolor.colored(f"packnow failed to fetch {args.url}", "red"))

        exit(1)

def main():
    parser = make_parser()

    args = parser.parse_args()

    if not args.subcmd:
        pack(args)
    elif args.subcmd == "host":
        host(args)
    elif args.subcmd == "get":
        receive(args)
    else:
        print("unknown command")
