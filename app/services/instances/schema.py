from typing import Literal, Annotated

from pydantic import BaseModel, Field



class _OSRule(BaseModel):

    version : str | None = None
    versionRange: str | None = None
    arch: str | None = None

class _Rule(BaseModel):
    action: Literal["allow", "disallow"]

    os: _OSRule | None = None
    features: dict[str, bool] | None = None




class VersionManifestV2(BaseModel):
    '''新版本的MC版本清单格式'''

    #region Arguments 
    class _Arguments(BaseModel):
        '''版本清单的参数'''

        class _ArgumentRules(BaseModel):
            rules: list[_Rule | _OSRule]
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
            class _Artifact(BaseModel):
                path: str
                sha1: str
                size: int
                url: str

            artifact: _Artifact

        downloads: '_LibraryDownload'

        name: str

        rules: list[_Rule | _OSRule] | None = None

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

      