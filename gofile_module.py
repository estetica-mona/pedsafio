import hashlib
import logging
import os
import fnmatch
import urllib.parse
from threading import Lock

import requests
from pathvalidate import sanitize_filename


logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s][%(funcName)20s()][%(levelname)-8s]: %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("GoFile")


class File:
    def __init__(self, link: str, dest: str):
        self.link = link
        self.dest = dest

    def __str__(self):
        return f"{self.dest} ({self.link})"


class Downloader:
    def __init__(self, token):
        self.token = token

    # Método para obtener el enlace de descarga del archivo
    def get_download_link(self, file: File):
        link = file.link
        return link  # Solo retorna el enlace de descarga directo


class GoFileMeta(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]


class GoFile(metaclass=GoFileMeta):
    def __init__(self) -> None:
        self.token = ""
        self.wt = ""
        self.lock = Lock()
        # Reuse a single Session to keep TCP connections alive and reduce latency
        self.session = requests.Session()

    def update_token(self) -> None:
        if self.token == "":
            try:
                resp = self.session.post("https://api.gofile.io/accounts", timeout=6)
                data = resp.json()
            except Exception as e:
                logger.error(f"update_token: request failed: {e}")
                raise
            if data.get("status") == "ok":
                self.token = data["data"]["token"]
                logger.info(f"updated token: {self.token}")
            else:
                logger.error(f"update_token: unexpected response: {data}")
                raise Exception("cannot get token")

    def update_wt(self) -> None:
        if self.wt == "":
            try:
                alljs = self.session.get("https://gofile.io/dist/js/global.js", timeout=6).text
            except Exception as e:
                logger.error(f"update_wt: request failed: {e}")
                raise
            if 'appdata.wt = "' in alljs:
                self.wt = alljs.split('appdata.wt = "')[1].split('"')[0]
                logger.info(f"updated wt: {self.wt}")
            else:
                logger.error("update_wt: unexpected global.js content")
                raise Exception("cannot get wt")

    def execute(self, dir: str, content_id: str = None, url: str = None, password: str = None, excludes: list[str] = None) -> None:
        files = self.get_files(dir, content_id, url, password, excludes)
        for file in files:
            download_link = Downloader(token=self.token).get_download_link(file)
            logger.info(f"Enlace de descarga para {file.dest}: {download_link}")

    def get_files(self, dir: str, content_id: str = None, url: str = None, password: str = None, excludes: list[str] = None) -> list:
        if excludes is None:
            excludes = []
        files = list()
        if content_id is not None:
            with self.lock:
                self.update_token()
                self.update_wt()
            hash_password = hashlib.sha256(password.encode()).hexdigest() if password != None else ""
            try:
                resp = self.session.get(
                    f"https://api.gofile.io/contents/{content_id}?wt={self.wt}&cache=true&password={hash_password}",
                    headers={
                        "Authorization": "Bearer " + self.token,
                    },
                    timeout=8,
                )
                data = resp.json()
            except Exception as e:
                logger.error(f"get_files: request failed for content_id={content_id}: {e}")
                return files
            logger.info(f"get_files: api response status={data.get('status')} for content_id={content_id}")
            logger.debug(f"get_files: api response data={data}")
            if data.get("status") == "ok":
                if data["data"].get("passwordStatus", "passwordOk") == "passwordOk":
                    if data["data"]["type"] == "folder":
                        dirname = data["data"]["name"]
                        dir = os.path.join(dir, sanitize_filename(dirname))
                        for (id, child) in data["data"]["children"].items():
                            if child["type"] == "folder":
                                # recurse into subfolders
                                files.extend(self.get_files(dir=dir, content_id=id, password=password, excludes=excludes))
                            else:
                                filename = child["name"]
                                if not any(fnmatch.fnmatch(filename, pattern) for pattern in excludes):
                                    files.append(File(
                                        link=urllib.parse.unquote(child["link"]),
                                        dest=urllib.parse.unquote(os.path.join(dir, sanitize_filename(filename)))))
                    else:
                        filename = data["data"]["name"]
                        if not any(fnmatch.fnmatch(filename, pattern) for pattern in excludes):
                            files.append(File(
                                link=urllib.parse.unquote(data["data"]["link"]),
                                dest=urllib.parse.unquote(os.path.join(dir, sanitize_filename(filename)))))
                else:
                    logger.error(f"invalid password: {data['data'].get('passwordStatus')}")
        elif url is not None:
            if url.startswith("https://gofile.io/d/"):
                files = self.get_files(dir=dir, content_id=url.split("/")[-1], password=password, excludes=excludes)
            else:
                logger.error(f"invalid url: {url}")
        else:
            logger.error(f"invalid parameters")
        return files


def convert_url_to_direct_links(url: str, password: str = None, max_results: int = 10) -> list:
    """Convierte un enlace normal de GoFile (`https://gofile.io/d/<id>`) a enlaces directos.

    Devuelve una lista de enlaces directos encontrados (máximo `max_results`).
    """
    gf = GoFile()
    files = gf.get_files(dir='.', url=url, password=password)
    links = [Downloader(token=gf.token).get_download_link(f) for f in files]
    return links[:max_results]


if __name__ == "__main__":
    # ejemplo rápido por si alguien ejecuta el módulo directamente
    import sys
    if len(sys.argv) > 1:
        url = sys.argv[1]
        links = convert_url_to_direct_links(url)
        for l in links:
            print(l)
