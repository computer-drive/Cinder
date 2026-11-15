from pathlib import Path
from threading import Event
from dataclasses import dataclass, field
from typing import Literal, Any
from queue import Queue
import hashlib

import requests

@dataclass
class DownloadMessage:
    id: int
    type: Literal["progress", "finished", "download_error", "canceled", "verify_error"]
    data: dict[str, Any] = field(default_factory=dict)

class Canceled(Exception):
    pass

class Downloader:
    def __init__(self,
                stop_event: Event,
                id: int,
                kind: str,
                url: str,
                sha1: str | None,
                path: Path,
                queue: Queue[DownloadMessage], 
        ):
        self.stop_event: Event                  = stop_event
        self.kind:       str                    = kind
        self.id:         int                    = id
        self.url:        str                    = url
        self.path:       Path                   = path
        self.queue:      Queue[DownloadMessage] = queue
        self.sha1:       str | None             = sha1


        
    def run(self):
        download_size = 0
        try:
            response = requests.get(self.url, stream=True, timeout=5)

            total = int(response.headers.get("Content-Length", 0))

            response.raise_for_status()

            with open(self.path, "wb") as f:
                
                for chunk in response.iter_content(chunk_size= 1024 * 1024): # 16KB

                    if self.stop_event.is_set():
                        raise Canceled()

                    f.write(chunk)

                    download_size += len(chunk)

                    self.queue.put(
                        DownloadMessage(
                            self.id, "progress",
                            {
                                "download_size": download_size,
                                "new_size": len(chunk),
                                "total": total,
                            }
                        )
                    )


        except requests.RequestException as e:
            self.queue.put(DownloadMessage(
                self.id, "download_error",
                {
                    "message": str(e) 
                }
            ))
        
        except Canceled:
            # 删除半成品文件
            if self.path.exists():
                self.path.unlink()

            self.queue.put(DownloadMessage(self.id, "canceled"))

        else:
            if self.sha1 is not None:
                # 校验sha1
                with open(self.path, "rb") as f:
                    sha1 = hashlib.sha1(f.read()).hexdigest()
                    if sha1 != self.sha1:
                        self.queue.put(DownloadMessage(self.id, "verify_error"))


            self.queue.put(DownloadMessage(self.id, "finished"))

        

            


