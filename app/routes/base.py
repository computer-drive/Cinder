from typing import Callable, Any
from enum import IntEnum

from flask import Blueprint, jsonify, request
from pydantic import BaseModel



class Response[T: IntEnum | int](BaseModel):
    status: T
    message: str = ""
    data: dict[str, Any]

class EmptyModel(BaseModel):
    pass

class CinderBlueprint(Blueprint):

    def __init__(self, name: str, url_prefix: str | None = None):
        super().__init__(name, __name__, url_prefix=url_prefix)

    def post[T: BaseModel, T_: IntEnum | int](self, path: str, params_type: type[T] = EmptyModel):
        

        def wrapper(f: Callable[[T], Response[T_]]):
        
            @self.route(path, methods=["POST"])
            def _wrapper():
                return jsonify(f(params_type(**request.json())).model_dump())


        return wrapper


    def get[T: BaseModel, T_: IntEnum | int](self, path: str):
            
    
            def wrapper(f: Callable[[], Response[T_]]):
            
                @self.route(path, methods=["GET"])
                def _wrapper():
                    return jsonify(f().model_dump())   
    
    
            return wrapper




    
