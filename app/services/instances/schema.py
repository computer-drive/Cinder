from typing import Literal, Any
import sys
import re
import platform
import struct

from pydantic import BaseModel



class _OSRule(BaseModel):

    version : str | None = None

    class _Range(BaseModel):
        min: str | None = None
        max: str | None = None

        def _parse(self, version: str):
            return tuple(int(x) for x in version.split(".") if x.isdigit())

        def in_range(self, version: str) -> bool:
            version_tuple = self._parse(version)
            if self.min:
                if not version_tuple >= self._parse(self.min):
                    return False
            
            if self.max:
                if not version_tuple <= self._parse(self.max):
                    return False

            return True


    versionRange: _Range | None = None

    arch: str | None = None
    name: str | None = None

class _Rule(BaseModel):
    action: Literal["allow", "disallow"]

    os: _OSRule | None = None
    features: dict[str, bool] | None = None


class _Context:
    platform_name: Literal["windows", "linux", "osx", "unknown"]
    short_version: str 
    full_version: str
    arch: str

    _instance = None
    _is_initialized = False
    def __new__(cls, *args: Any, **kwargs: Any): 
        if cls._instance is None:
            cls._instance = super().__new__(cls)

        return cls._instance

    def __init__(self):
        if self._is_initialized:
            return

        self._is_initialized = True
        
        self.platform_name = {  # pyright: ignore[reportAttributeAccessIssue]
            "win32": "windows",
            "linux": "linux",
            "darwin": "osx"
        }.get(sys.platform, "unknown")

        match self.platform_name:
            case "windows":
                v = sys.getwindowsversion()
                self.short_version  = f"{v.major}.{v.minor}"
                self.full_version   = f"{v.major}.{v.minor}.{v.build}"
            case "linux":
                self.short_version  = platform.release()
                self.full_version   = self.short_version.split("-")[0]
            case "osx":
                self.short_version  = platform.mac_ver()[0] or platform.release()
                self.full_version   = self.short_version
                
            case "unknown":
                self.short_version  = ""
                self.full_version   = ""

        self.arch = "x86" if struct.calcsize("P") * 8 == 32 else "x86_64"



def match_rules(rules: list[_Rule], features: dict[str, bool]) -> bool:
    '''判断是否符合规则'''

    ctx = _Context()

    if ctx.platform_name == "unknown":
        return False

    if not rules:
        return True

    def match(rule: _Rule) -> bool:
        conform = True
        if rule.os:
            
            if rule.os.name == ctx.platform_name:
                if rule.os.version:
                    # 旧版是正则表达式匹配
                    # 获取粗略的版本号
                    conform = re.fullmatch(rule.os.version, ctx.short_version) is not None

                elif rule.os.versionRange:
                    # 新版是版本范围匹配
                    conform = rule.os.versionRange.in_range(ctx.full_version)

                else:
                    conform = True
            else:
                conform = False

            if rule.os.arch:
                conform = conform and rule.os.arch == ctx.arch

        if conform:
            if rule.features:
                for feature, value in rule.features.items():
                    if features.get(feature, None) != value:
                        return False
            
            return True
        else:
            return False


    finally_allow = False
    for rule in rules:
        if match(rule):
            finally_allow = rule.action == "allow"
        
    
    return finally_allow




class VersionManifestV2(BaseModel):
    '''新版本的MC版本清单格式'''

    #region Arguments 
    class _Arguments(BaseModel):
        '''版本清单的参数'''

        class _ArgumentRules(BaseModel):
            rules: list[_Rule]
            value: str | list[str]

        game: list[str | _ArgumentRules]
        jvm: list[str | _ArgumentRules]


        

    arguments: _Arguments
    #endregion

    #region AssetIndex
    class _AssetIndex(BaseModel):
        id: str
        sha1: str
        size: int
        totalSize: int
        url: str

    assetIndex: _AssetIndex
    #endregion

    
    #region Downloads
    class _Downloads(BaseModel):

        class _DownloadInfo(BaseModel):
            sha1: str
            size: int
            url: str

        client: _DownloadInfo

    downloads: _Downloads
    #endregion

    class _JavaVersion(BaseModel):
        component: str
        majorVersion: int

    javaVersion: _JavaVersion

    class _Libraries(BaseModel):

        class _LibraryDownload(BaseModel):
            class _DownloadInfo(BaseModel):
                path: str
                sha1: str
                size: int
                url: str

            artifact: _DownloadInfo | None

            classifiers: dict[str, _DownloadInfo] | None

        downloads: '_LibraryDownload'

        name: str

        rules: list[_Rule] | None = None

        natives: dict[str, str] | None = None

    libraries: list[_Libraries]



    class _Logging(BaseModel):

        class _Client(BaseModel):
            argument: str

            class _File(BaseModel):
                id: str
                sha1: str
                size: int
                url: str

            file: _File

            type: str

        client: _Client

    logging: _Logging

    mainClass: str


class AssetsObjects(BaseModel):

    class _Objects(BaseModel):
        hash: str
        size: int

    objects: dict[str, _Objects]

    vitural: bool = False
    map_to_resources: bool = False

      