from typing import Literal
import time

lazy from pydantic import BaseModel, ValidationError, computed_field
lazy import requests

from ..database import use_database
from ..database.model import MCVersions

from .base import Task, StepFinished, StepUpdate, TaskError



VERSION_MANIFEST_URL = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"

class VersionManifest(BaseModel):

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
            manifest = VersionManifest(**response.json())
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

        
                
class InstancesService:
    def __init__(self):
        self.fetch_versions = FetchVersions

        self.fetch_version_manifest = FetchVersionManifest
