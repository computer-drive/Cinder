from dataclasses import dataclass, field
from typing import Any, Union, Generator, Generic, TypeVar



@dataclass
class StepUpdate:
    '''任务状态更新的标志'''
    step: str
    data: dict[str, Any] = field(default_factory=dict)
    
@dataclass
class StepFinished:
    '''此步骤已完成的标志'''
    step: str
    data: dict[str, Any] = field(default_factory=dict)
    is_error: bool = False

class TaskError(Exception):
    def __init__(self, message: str, data: dict[str, Any] | None = None):
        self.message = message
        self.data = data

        super().__init__(message)



Event = Union[StepUpdate, StepFinished]

T = TypeVar("T")

class Task(Generic[T]):
    
    def run_complete(self) -> T:
        '''完整执行此任务'''
        task = self.run()

        try:
            while True:
                next(task)

        except StopIteration as e:
            return e.value

        finally:
            task.close()
        
    def run(self) -> Generator[Event, None, T]:
        '''运行任务'''
        raise NotImplementedError


        
        
    