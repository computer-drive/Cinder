from typing import Literal,  Any, cast
import time
from threading import Thread, Event
from enum import Enum
from queue import Queue, Empty
import os
from datetime import datetime
import json
from dataclasses import dataclass

lazy from pydantic import BaseModel, ValidationError, computed_field, TypeAdapter
lazy from playhouse.shortcuts import model_to_dict
lazy import requests

from core.utils.path import path_legalize
from ...paths import paths
from ...database import use_database
from ...database.model import (MCLibraries, LibrariesReference, AssetsReference,
    MCVersions, MCArguments, MCAssetsIndex, MCAssetsObjects, Files, Instances
)
from ..base import Task, StepFinished, StepUpdate, TaskError
from .schema import VersionManifestV2, AssetsObjects, match_rules, _Context, Rule
from .downloader import Downloader, DownloadMessage

VERSION_MANIFEST_URL = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"

ASSETS_OBJECTS_URL = "https://resources.download.minecraft.net/"


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

class UpdateVersionsIndex(Task[dict[str, Any]]):
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

class UpdateVersionManifest(Task[dict[str, Any]]):
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

            yield StepUpdate("fetch_manifest.cache")

        else:
            # 缓存不存在
            response = requests.get(version_info.url)
            response.raise_for_status()

            data = response.json()

            # 缓存
            with open(cache_path, "w") as f:
                json.dump(response.json(), f)

            yield StepUpdate("fetch_manifest.network")

        yield StepFinished("analyze_manifest")

        if data.get("arguments", None) is not None:
            # V2清单
            try:
                manifest = VersionManifestV2(**data)
            except ValidationError as e:
                raise TaskError("unknown_manifest_type", {
                    "message": str(e),
                    "data": data
                })

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

                
                #region 解析libraries
                libraries = []

                found_artifacts = set()

                for library in manifest.libraries:
                    hit = False

                    if library.rules is not None:
                        # 判断库是否符合规则
                        if not match_rules(library.rules, {}):
                            # 若不符合，则跳过
                            continue

                

                    if library.downloads.artifact is not None:
                        # 若有artifact，则添加到列表，不是native库
                        hit = True

                        # 判断maven_path已经在found_artifacts中
                        if library.downloads.artifact.path in found_artifacts:
                            # 若在，则跳过
                            continue

                        
                        found_artifacts.add(library.downloads.artifact.path)

                        libraries.append({
                            "name": library.name,
                            "sha1": library.downloads.artifact.sha1,
                            "size": library.downloads.artifact.size,
                            "url": library.downloads.artifact.url,
                            "maven_path": library.downloads.artifact.path,
                            "is_native": False,
                            "version": version_info,
                            "rules": [rule.model_dump() for rule in library.rules] if library.rules else None,
                        })

                    
                    if library.natives is not None:
                        # 若有natives库，添加到列表，是native库
                        if library.downloads.classifiers is None:
                            # 没有natives的包，直接跳过
                            continue

                        hit = True


                        ctx = _Context()

                        # 根据平台匹配
                        classifier_name = library.natives.get(ctx.platform_name, None)

                        if classifier_name is None:
                            # ! 注意，此错误大概率不会发生，除非mojang的数据写错了
                            raise TaskError("native_library.platform_not_supported", {
                                "library_name": library.name,
                                "supported_platforms": library.natives.keys(),
                            })

                        else:
                            
                            # 若有classifier，则添加到列表，是native库
                            libraries.append({
                                "name": library.name,
                                "sha1": library.downloads.classifiers[classifier_name].sha1,
                                "size": library.downloads.classifiers[classifier_name].size,
                                "url": library.downloads.classifiers[classifier_name].url,
                                "maven_path": library.downloads.classifiers[classifier_name].path,
                                "is_native": True,
                                "version": version_info,
                                "rules": [rule.model_dump() for rule in library.rules] if library.rules else None,
                            })
                        
                    if not hit:
                        yield StepUpdate("libraries.unused", {
                            "library_name": library.name,
                        })
                    #endregion
                        

                MCLibraries.insert_many(libraries).execute()

                assets_index, created = MCAssetsIndex.get_or_create(
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
            raise TaskError("unknown_manifest_type", {
                "message": "未知的清单类型。",
            })
       


THREAD_COUNT = 16

@dataclass
class _Reference:
    kind: Literal["client", "assets", "library"]
    meta: MCLibraries | MCAssetsObjects
    sha1: str

class InstallInstance(Task[dict[str, Any]]):

    class State(Enum):
        VERSION_NOT_FOUND = "version_not_found"
        VERSION_UNFETCHED = "version_unfetched"
        ASSETS_NOT_FOUND = "assets_not_found"
        DOWNLOADING = "downloading"

        CANCELED = "canceled"

        CANCELING = "canceling"

    


    def __init__(self, version: str, stop_event: Event):
        self.version: str = version
        self.database = use_database()

        self.stop_event = stop_event

        self.exist_assets: list[MCAssetsObjects] = []
        self.exist_libraries: list[MCLibraries] = []

        self.instance_name: str = ""

        self.references: list[_Reference] = []
        self.references_map: dict[str, _Reference] = {}

        self.references_file: dict[str, Files] = {}

    def get_not_exist_assets(self, all_objects: list[MCAssetsObjects]):
        # 先查询所有的objects

        hash_map = {obj.hash: obj for obj in all_objects}

        # 查找Files表中所有存在的objects
        existing_hashs = [file.sha1 for file in (
            Files.select()
            .where(Files.sha1.in_(list(hash_map.keys())))
        )]

        # 过滤出不存在的objects
        not_exist_assets: list[MCAssetsObjects] = []
        exist_assets: list[MCAssetsObjects] = []

        for obj in all_objects:
            if obj.hash in existing_hashs:
                exist_assets.append(obj)
            else:
                not_exist_assets.append(obj)
        
        return not_exist_assets, exist_assets

    def get_not_exist_libraries(self, all_libraries: list[MCLibraries]):
        # 先查询所有的libraries
        hash_map = {lib.sha1: lib for lib in all_libraries}

        # 查找Files表中所有存在的libraries
        existing_hashs = [file.sha1 for file in (
            Files.select()
            .where(Files.sha1.in_(list(hash_map.keys())))
        )]

        # 过滤出不存在的libraries
        not_exist_libraries: list[MCLibraries] = []
        exist_libraries: list[MCLibraries] = []

        for lib in all_libraries:
            if lib.sha1 in existing_hashs:
                exist_libraries.append(lib)
            else:
                not_exist_libraries.append(lib)

        return not_exist_libraries, exist_libraries

    def run(self):
        version_info: MCVersions | None = MCVersions.get_or_none(version=self.version)

        if version_info is None:
            raise TaskError(self.State.VERSION_NOT_FOUND.value)

        elif version_info.fetched_at is None:
            raise TaskError(self.State.VERSION_UNFETCHED.value)

        count = 0
        total_size: int = 0
        downloaders : dict[int, Downloader] = {}

        stop_event = self.stop_event
        progress_queue: Queue[DownloadMessage] = Queue()

        #region 添加client下载

        # 先判断是否已经存在client文件
        if Files.get_or_none(sha1=version_info.client_sha1) is None:
            # 若不存在，则添加下载器
            downloaders[count] = Downloader(
                stop_event,
                count,
                "client",
                version_info.client_files, #pyright: ignore[reportArgumentType]
                version_info.client_sha1,
                paths.instances / f"{self.version}.jar",
                progress_queue
            )
            total_size += cast(int, version_info.client_size)

        #endregion

        #region 添加assets下载
        not_exist_assets, self.exist_assets = self.get_not_exist_assets(list(
                    MCAssetsObjects.select(MCAssetsObjects.hash, MCAssetsObjects.size)
                    .where(MCAssetsObjects.assets_index == version_info.assets)
                    .group_by(MCAssetsObjects.hash)

                ))

        for asset in not_exist_assets:
            count += 1

            object_path = paths.assets_objects / asset.hash[:2]

            object_path.mkdir(parents=True, exist_ok=True)

            downloaders[count] = Downloader(
                stop_event,
                count,
                "assets",
                ASSETS_OBJECTS_URL + asset.hash[:2] + "/" + asset.hash,
                asset.hash,
                object_path / asset.hash,
                progress_queue
            )

            total_size += asset.size

        self.references.extend(
            [_Reference(kind="assets", sha1=asset.hash, meta=asset) 
            for asset in not_exist_assets + self.exist_assets
        ])

        #endregion
        
        #region 添加libraries下载
        not_exist_libraries, self.exist_libraries = self.get_not_exist_libraries(list(
            MCLibraries.select()
            .where(MCLibraries.version == version_info)
        ))

        self.references.extend(
            [_Reference(kind="library", sha1=lib.sha1, meta=lib) 
            for lib in not_exist_libraries + self.exist_libraries
        ])

        rule_adapter = TypeAdapter(list[Rule])

        for library in not_exist_libraries:
            count += 1
            
            if library.rules is not None:
                # 若规则不为空，则判断是否符合规则
                if not match_rules(rule_adapter.validate_python(library.rules), {}):
                    # 不符合跳过
                    continue

            if library.is_native:
                downloaders[count] = Downloader(
                    stop_event,
                    count,
                    "libraries",
                    library.url,
                    library.sha1,
                    paths.natives / (path_legalize(library.name) + ".jar"),
                    progress_queue
                )

                total_size += library.size
            else:
                downloaders[count] = Downloader(
                    stop_event,
                    count,
                    "libraries",
                    library.url,
                    library.sha1,
                    paths.libraries / (path_legalize(library.name) + ".jar"),
                    progress_queue
                )
                
                total_size += library.size
        #endregion
        
        # TODO: 日志config的xml下载

        # 为references生成map
        self.references_map = {reference.sha1: reference for reference in self.references}

        if len(downloaders) != 0:
            yield StepFinished(self.State.DOWNLOADING.value, {
                "total_size": total_size,
                "count": len(downloaders),
            })

            downloader_queue: Queue[Downloader] = Queue()  # 用于主线程和下载线程之间的通信，池大小为8个
            writer_database_queue: Queue[Files] = Queue()

            def worker(downloader_queue: Queue[Downloader], stop_event: Event):
                session = requests.Session()

                while True:
                    if stop_event.is_set():
                        break
                    
                    try:
                        downloader = downloader_queue.get(timeout=0.1)
                    except Empty:
                        continue

                    downloader.run(session)

                    downloader_queue.task_done()

            def writer_worker(writer_database_queue: Queue[Files], stop_event: Event):
                buffer: list[Files] = []


                while True:
                    if stop_event.is_set():
                        break
                    
                    try:
                        file = writer_database_queue.get(timeout=0.1)
                    except Empty:
                        continue

                
                    buffer.append(file)

                    if len(buffer) >= 50 or stop_event.is_set():
                        try:
                            with Files._meta.database.atomic():
                                Files.insert_many(
                                    [model_to_dict(file) for file in buffer]
                                ).execute()
                        except Exception as e:
                            print("Error: ", e)
                            for file in buffer:
                                print(file.path, file.sha1)

                        # 如果写入成功，就更新references_file
                        self.references_file[file.sha1] = file

                        # for file in buffer:
                        #     try:
                        #         Files.create(**model_to_dict(file))
                        #     except Exception as e:
                        #         print("Error: ", e)
                        #         print(file.path, file.sha1)



                        buffer.clear()
                    
                    
                    writer_database_queue.task_done()
            
            writer_thread = Thread(target=writer_worker, args=(writer_database_queue, stop_event))
            threads: list[Thread] = [Thread(target=worker, args=(downloader_queue, stop_event)) for _ in range(THREAD_COUNT)]

            for t in threads:
                t.start()
            
            writer_thread.start()



            current_downloaders: list[Downloader] = []

            downloaders_list = list(downloaders.values())

            error_downloaders: list[Downloader] = []

            try:
                while True:

                    while len(current_downloaders) < THREAD_COUNT:
                        if not downloaders_list:
                            break
                            
                        new_downloader = downloaders_list.pop(0)
                        
                        current_downloaders.append(new_downloader)

                        downloader_queue.put(new_downloader)

                        yield StepUpdate("new_download_started", {
                            "thread": current_downloaders.index(new_downloader),
                            "id": new_downloader.id,
                        })
                    

                    try:
                        message = progress_queue.get(timeout=0.1)
                    except Empty:
                        continue


                    downloader = downloaders[message.id]
                    
                    if message.type in ["download_error", "verify_error"]:
                        current_downloaders.remove(downloader)

                        error_downloaders.append(downloader)

                    elif message.type == "finished":
                        current_downloaders.remove(downloader)

                        writer_database_queue.put(Files(
                            path=os.path.relpath(downloader.path, paths.data),
                            sha1=downloader.sha1,
                            size=message.data["size"],
                            created_at=datetime.now(),
                        ))

                    if not current_downloaders and not downloaders_list:
                        # 当所有下载器都完成时，且没有新的下载器时，跳出循环
                        break

                    thread: int = -1
                    for i, downloader in enumerate(current_downloaders):
                        if downloader.id == message.id:
                            thread = i
                            break
            
                    yield StepUpdate("download_progress", {
                                    "id": message.id,
                                    "thread": thread,
                                    "type": message.type,
                                    "data": message.data
                                })

            except KeyboardInterrupt:
                stop_event.set()


                yield StepFinished(self.State.CANCELING.value)
                
                for t in threads:
                    t.join()
                
                yield StepFinished(self.State.CANCELED.value, {})


            stop_event.set()


            writer_thread.join()

        
            for t in threads:
                t.join()
            
            if len(error_downloaders) > 0 :
                yield StepUpdate("has_error", {
                    "count": len(error_downloaders)
                })
                return False

            yield StepFinished("download_all_finished")

        else:
            yield StepFinished("download_aleady_finished")


        while True:
            yield StepFinished("input_instance_name")

            if Instances.get_or_none(name=self.instance_name) is None:
                break
            else:
                yield StepUpdate("instance_name_exists", {})



        # 构建引用关系
        yield StepFinished("building_references", {
            "total": len(self.references),
        })

        count = 0
        
        with self.database.atomic():
            instance = Instances.create(
                name=self.instance_name,
                version=version_info,
                client_file=self.references_map[cast(str, version_info.client_sha1)],
            )

            for reference in self.references:  
                if reference.kind == "library":
                    LibrariesReference.create(
                        library_file=self.references_file[reference.sha1],
                        instance=instance,
                        library=reference.meta,
                    )
                elif reference.kind == "assets":

                    AssetsReference.create(
                        asset_file=Files.get(sha1=reference.sha1),
                        instance=instance,
                        asset=reference.meta,
                    )
                count += 1

                yield StepUpdate("building_progress", {
                    "finished": count,
                    "total": len(downloaders),
                })

        return True

          
class InstancesService:
    def __init__(self):
        self.update_versions_index = UpdateVersionsIndex

        self.fetch_version_manifest = UpdateVersionManifest

        self.install_instance = InstallInstance
