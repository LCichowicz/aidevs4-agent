from dataclasses import dataclass,field
from typing import Any

@dataclass
class PlanStep:
    tool : str 
    input: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        
        if not isinstance(self.tool,str):
            raise TypeError(f"{self.tool} has to be 'string'")
        
        if len(self.tool.strip()) == 0:
            raise ValueError(f"{self.tool} cannot be empty 'string'")
        
        if not isinstance(self.input, dict):
            raise TypeError(f"{self.input} has to be 'dict'")
        

@dataclass
class Plan:
    steps: list[PlanStep] = field(default_factory=list)


@dataclass
class AgentContext:
    context : str = ""
    user_input : str = "" 