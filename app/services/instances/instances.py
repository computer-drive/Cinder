from typing import Literal, TypedDict, Any
import time
from threading import Thread, Event
from queue import Queue
import os
import hashlib
from datetime import datetime
import json

lazy from pydantic import BaseModel, ValidationError, computed_field
lazy import requests

from ...database import use_database
from ...database.model import MCLibraries, MCVersions, MCArguments, MCAssetsIndex, MCAssetsObjects

from ..base import Task, StepFinished, StepUpdate, TaskError
from ...paths import paths

from .schema import VersionManifestV2, AssetsObjects

VERSION_MANIFEST_URL = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"


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


    

class UpdateVersionsIndex(Task):
    '''更新mc版本索引清单'''
    def __init__(self):
        pass

    def run(self):
        start_time = time.time()

        response = requests.get(VERSION_MANIFEST_URL)

        try:
            manifest = VersionIndexManifest(**response.json())
        except ValidationError as e:
            raise TaskError("版本清单解析失败。", {
                "message": str(e),
                "data": response.json()
            })

        yield StepFinished("analyze_manifest", {
            "time_taken": time.time() - start_time
        })

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
        } for name in not_exist_versions]

        # 批量插入
        with database.atomic():
            MCVersions.insert_many(data).execute()

        return {
            "new_versions_count": len(not_exist_versions),
            "time_taken": time.time() - start_time
        }

class UpdateVersionManifest(Task):
    '''获取一个版本的清单数据'''

    def __init__(self, version: str):
        self.version = version

    def run(self):
        database = use_database(MCVersions)

        # 查询数据库记录
        version_info = MCVersions.get_or_none(MCVersions.version == self.version)

        if version_info is None:
            # 版本不存在
            raise TaskError("version_not_found")
        
        elif version_info.fetched_at != None:
            # 已经获取过了
            yield StepUpdate("version_data_already_fetched")
            return version_info

        response = None

        # 查询缓存
        cache_path = paths.cache / version_info.sha1
        if cache_path.exists():
            # 缓存存在
            with open(cache_path, "r") as f:
                data = json.load(f)

        else:
            # 缓存不存在
            response = requests.get(version_info.url)
            response.raise_for_status()

            data = response.json()

            # 缓存
            with open(cache_path, "w") as f:
                json.dump(response.json(), f)



        if data.get("arguments", None) is not None:
            # V2清单
            manifest = VersionManifestV2(**data)

            # 获取assets objects
            # 读取缓存
            cache_path = paths.cache / manifest.assetIndex.sha1
            # print(cache_path)
            if cache_path.exists():

                with open(cache_path, "r") as f:
                    assets_data = json.load(f)
            else:
                # 缓存不存在
                response = requests.get(manifest.assetIndex.url)
                response.raise_for_status()

                assets_data = response.json()

                # 缓存
                with open(cache_path, "w") as f:
                    json.dump(response.json(), f)

            # 解析assets objects
            # print(assets_data)
            assets_objects = AssetsObjects(**assets_data)

            
            # 更新数据库记录
            with database.atomic():
                MCArguments.insert(
                    version= version_info,
                    jvm    = [jvm if isinstance(jvm, str) else jvm.model_dump() for jvm in manifest.arguments.jvm],
                    game   = [game if isinstance(game, str) else game.model_dump() for game in manifest.arguments.game]
                ).execute()

                MCLibraries.insert_many([
                    {
                        "version": version_info,
                        "name": library.name,
                        "sha1": library.downloads.artifact.sha1,
                        "size": library.downloads.artifact.size,
                        "url": library.downloads.artifact.url,
                        "maven_path": library.downloads.artifact.path,
                    } for library in manifest.libraries 
                ]).execute()

                assets_index = MCAssetsIndex.create(
                    id               = manifest.assetIndex.id,
                    sha1             = manifest.assetIndex.sha1,
                    size             = manifest.assetIndex.size,
                    total_size       = manifest.assetIndex.totalSize,
                    url              = manifest.assetIndex.url,
                    virtual          = assets_objects.vitural,
                    map_to_resources = assets_objects.map_to_resources,
                )

                # 插入assets objects
                MCAssetsObjects.insert_many([
                    {
                        "assets_index": assets_index,
                        "name": name,
                        "hash": value.hash,
                        "size": value.size,
                    } for name, value in assets_objects.objects.items()
                ]).execute()

                version_info.fetched_at   = datetime.now()
                version_info.assets       = assets_index
                version_info.main_class   = manifest.mainClass
                version_info.java_major   = manifest.javaVersion.majorVersion
                version_info.client_files = manifest.downloads.client.url
                version_info.client_sha1  = manifest.downloads.client.sha1
                version_info.client_size  = manifest.downloads.client.size

                version_info.logging_argument = manifest.logging.client.argument
                version_info.logging_file = manifest.logging.client.file.model_dump()
                version_info.save()



        elif data.get("minecraftArguments", None) is not None:
            # V1清单
            # ! TODO
            raise NotImplementedError("V1清单未实现")
        else:
            raise TaskError("unknown_manifest_type")

        

        






class UpdateMessage(TypedDict):
    type: str
    data: dict[str, Any]

# ! WIP
class DownloadInstance(Task):

    def __init__(self, version: str, deeply: bool):
        self.version = version
        self.deeply = deeply

        self.database = use_database(MCVersions, ClientFiles)

        self.stop_event = Event()

    def _download_client_file(self, queue: Queue[UpdateMessage], version_data: VersionManifest, ):
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
            return 
        
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

        is_error = False

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

                is_error = True
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
            is_error = True

        except requests.RequestException as e:
            is_error = True
            raise TaskError("download_error", {
                "message": str(e)
            })

        except Exception as e:
            is_error = True
            raise e
            


        finally:
            if is_error:
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

    
    def _download_libraries_file(self, queue: Queue[UpdateMessage], version_data: VersionManifest, ):
        pass

    

    def run(self):

        if self.deeply:
            yield StepFinished("updating_version_manifest")
            try:
                UpdateVersionsIndex().run_complete()
            except TaskError as e:
                raise TaskError("failed_to_update_version_manifest", e.data["message"]) #type: ignore

            try:
                UpdateVersionManifest(self.version).run_complete()
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
        self.update_versions_index = UpdateVersionsIndex

        self.fetch_version_manifest = UpdateVersionManifest
