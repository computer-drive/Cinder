from typing import Literal, TypedDict, Any
import time
from threading import Thread, Event
from queue import Queue
import os
import hashlib
from datetime import datetime

lazy from pydantic import BaseModel, ValidationError, computed_field
lazy import requests

from ..database import use_database
from ..database.model import MCVersions, ClientFiles

from .base import Task, StepFinished, StepUpdate, TaskError
from ..paths import paths

VERSION_MANIFEST_URL = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"


class VersionManifest:
    class _DownloadInfo(TypedDict):
        url: str
        size: int
        sha1: str

    class _AssetsInfo(TypedDict):
        id: str
        sha1: str
        size: int
        url: str

    class _JavaInfo(TypedDict):
        component: str
        majorVersion: int

    assets: _AssetsInfo    
    downloads: _DownloadInfo
    java: _JavaInfo
    

    def __init__(self, data: dict):
        self.data = data

        self.downloads = data["downloads"]["client"]
        self.assets = data["assetIndex"]
        self.java = data["javaVersion"]

class VersionIndexManifest(BaseModel):

    class _Version(BaseModel):
        id: str
        type: Literal["release", "snapshot", "old_beta", "old_alpha"]
        url: str
        releaseTime: str
        sha1: str
        complianceLevel: Literal[1, 0]

    versions: list[_Version]

    @computed_field
    @property
    def versions_map(self) -> dict[str, _Version]:
        return {v.id: v for v in self.versions}

class FetchVersions(Task):
    '''更新mc版本索引清单'''
    def __init__(self):
        pass

    def run(self):

        response = requests.get(VERSION_MANIFEST_URL)

        try:
            manifest = VersionIndexManifest(**response.json())
        except ValidationError as e:
            raise TaskError("版本清单解析失败。", {
                "message": str(e),
                "data": response.json()
            })

        yield StepFinished("analyze_manifest")
        start_time = time.time()

        database = use_database(MCVersions)

        manifest_map = manifest.versions_map

        new_versions_set = set(manifest_map.keys()) # 新的版本
        db_versions_set = set([v.version for v in MCVersions.select()]) # 数据库中的版本

        # 去重
        not_exist_versions = new_versions_set - db_versions_set

        # 生成不存在的版本记录
        data = [{
            "version": manifest_map[name].id,
            "type": manifest_map[name].type,
            "url": manifest_map[name].url,
            "time": manifest_map[name].releaseTime,
            "sha1": manifest_map[name].sha1,
            "is_safety": manifest_map[name].complianceLevel == 1,
            "data": None,
            "fetchd_at": None
        } for name in not_exist_versions]

        # 批量插入
        with database.atomic():
            MCVersions.insert_many(data).execute()

        return {
            "new_versions_count": len(not_exist_versions),
            "time_taken": time.time() - start_time
        }

class FetchVersionManifest(Task):
    '''获取一个版本的清单数据'''

    def __init__(self, version: str):
        self.version = version

    def run(self):
        database = use_database(MCVersions)

        # 获取
        version_info = MCVersions.get_or_none(MCVersions.version == self.version)

        if version_info is None:
            raise TaskError("version_not_found")
        
        elif version_info.data != None:
            yield StepUpdate("version_data_already_fetched")
            return version_info.data

        res_ = requests.get(version_info.url)

        if res_.status_code != 200:
            raise TaskError("fetch_error", {
                "status_code": res_.status_code
            })

        try:
            res_.json()
        except Exception as e:
            raise TaskError("response_error", {
                "message": str(e)
            })
        
        with database.atomic():
            version_info.data = res_.json()

            version_info.save()

        return version_info.data


class UpdateMessage(TypedDict):
    type: str
    data: dict[str, Any]

class DownloadInstance(Task):

    def __init__(self, version: str, deeply: bool):
        self.version = version
        self.deeply = deeply

        self.database = use_database(MCVersions, ClientFiles)

        self.stop_event = Event()

    def _donwload_client_file(self, queue: Queue[UpdateMessage], version_data: VersionManifest, ):
        '''下载客户端文件'''
        # 分析客户端文件是否存在
        client_file = ClientFiles.get_or_none(sha1=version_data.downloads["sha1"])

        if client_file is not None:
            # 已经下载了
            queue.put({
                "type": "finished",
                "data": {
                    "extra": "already_exist",
                    "path": client_file.path,
                    "id": client_file.id
                }
            })
        
        # 下载
        file_path = paths.instances / f"{version_data.downloads['sha1']}.jar"

        downloaded_size = 0
        last_report = 0

        queue.put({
            "type": "update_progress",
            "data": {
                "downloaded": downloaded_size,
                "total": version_data.downloads["size"]
            }
        })

        try:
            with requests.get(version_data.downloads["url"], stream=True) as res:
                res.raise_for_status() 
                with open(file_path, "wb") as f:
                    for chunk in res.iter_content(chunk_size=64 * 1024): # 64 KiB

                        if self.stop_event.is_set():
                            raise KeyboardInterrupt
                        
                        if not chunk:
                            continue

                        f.write(chunk)

                        downloaded_size += len(chunk)

                        if downloaded_size - last_report >= 1024 * 1024:
                            queue.put({
                                "type": "update_progress",
                                "data": {
                                    "downloaded": downloaded_size,
                                    "total": version_data.downloads["size"]
                                }
                            })

                            last_report = downloaded_size

        

            # 下载完成，验证sha1
            queue.put({
                "type": "verifing",
                "data": {}
            })

            # 计算sha1
            with open(file_path, 'rb') as f:
                file_hash = hashlib.file_digest(f, "sha1").hexdigest()

            if file_hash != version_data.downloads["sha1"]:
                queue.put({
                    "type": "verify_error",
                    "data": {}
                })

                # 删除半成品文件
                try:
                    os.remove(file_path)
                except OSError:
                    # 可能出现文件不存在，不用管
                    pass

                return
            
            # 验证通过，更新数据库记录

            with self.database.atomic():
                file = ClientFiles.create(
                    sha1=version_data.downloads["sha1"],
                    path=file_path,
                    size=downloaded_size,
                    created_at=datetime.now()
                )

                file.save()


            queue.put({
                "type": "finished",
                "data": {
                    "path": file_path,
                    "id": file.id,
                    "extra": ""
                }
            })

        except KeyboardInterrupt:
            queue.put({
                "type": "canceling",
                "data": {}
            })

            # 删除半成品文件
            try:
                os.remove(file_path)
            except OSError:
                # 可能出现文件不存在，不用管
                pass

            queue.put({
                "type": "canceled",
                "data": {}
            })


        except requests.RequestException as e:
            raise TaskError("download_error", {
                "message": str(e)
            })

    

    def run(self):

        if self.deeply:
            yield StepFinished("updating_version_manifest")
            try:
                FetchVersions().run_complete()
            except TaskError as e:
                raise TaskError("failed_to_update_version_manifest", e.data["message"]) #type: ignore

            try:
                FetchVersionManifest(self.version).run_complete()
            except TaskError as e:
                if e.message == "version_not_found":
                    raise TaskError("version_not_found") #type: ignore
                else:
                    raise TaskError("failed_to_update_version_manifest", e.data) #type: ignore

        yield StepFinished("analyze_download_files")


        version_info = MCVersions.get_or_none(MCVersions.version == self.version)
        if version_info is None:
            raise TaskError("version_not_found")

        version_data: VersionManifest = VersionManifest(version_info.data)


        
        
                
class InstancesService:
    def __init__(self):
        self.fetch_versions = FetchVersions

        self.fetch_version_manifest = FetchVersionManifest
