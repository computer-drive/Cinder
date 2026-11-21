from typing import Any

def _snake_to_camel(snake_str: str) -> str:
    '''将下划线命名法转换为驼峰命名法'''
    if not snake_str:
        return ""

    # 按下划线分割，并过滤掉空字符（防止连续下划线导致多余的空片段）
    parts = [p for p in snake_str.split("_") if p]
    if not parts:
        return ""

    # 第一个单词全小写（或保持原样），后面的单词首字母大写
    return parts[0].lower() + "".join(word.capitalize() for word in parts[1:])

def dkeys_snake_to_camel(d: dict[str, Any]) -> dict[str, Any]:
    '''将字典的所有键从下划线命名法转换为驼峰命名法'''
    return {_snake_to_camel(k): v for k, v in d.items()}

def get_object_property(obj: Any):
    properties: dict[str, Any] = {}

    for key, value in obj.__dict__.items():
        properties[_snake_to_camel(key)] = value

    return properties

if __name__ == "__main__":
    print(_snake_to_camel("ms_refresh_token"))
