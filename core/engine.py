"""
Mega Brain Core Engine — Orchestrator, State Manager, Pipeline Runner.

The engine that powers the entire Mega Brain system.
Manages agent lifecycle, pipeline execution, state persistence,
and coordinates all subsystems.
"""

import json
import time
import uuid
from pathlib import Path
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class AgentStatus(Enum):
    IDLE = "idle"
    WORKING = "working"
    DONE = "done"
    ERROR = "error"


class PipelineStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class StateManager:
    """Manages system state and persistence to state.json."""

    def __init__(self, state_path: str = "state.json"):
        self.path = Path(state_path)
        self.state = self._load()

    def _load(self) -> dict:
        if self.path.exists():
            return json.loads(self.path.read_text())
        return {
            "system": "Mega Brain",
            "version": "1.0.0",
            "status": PipelineStatus.PENDING.value,
            "agents": {},
            "pipeline": {"current_step": None, "steps": []},
            "dashboard": {"active": False, "clients": 0},
            "history": [],
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

    def save(self):
        self.state["updated_at"] = datetime.utcnow().isoformat()
        self.path.write_text(json.dumps(self.state, indent=2, ensure_ascii=False))
        return self

    def set_agent_status(self, agent_name: str, status: AgentStatus, data: Optional[dict] = None):
        self.state["agents"][agent_name] = {
            "status": status.value,
            "updated_at": datetime.utcnow().isoformat(),
            "data": data or {},
        }
        self.save()
        return self

    def set_pipeline_step(self, step: str, status: str, data: Optional[dict] = None):
        self.state["pipeline"]["current_step"] = step
        self.state["pipeline"]["steps"].append({
            "step": step,
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data or {},
        })
        self.save()
        return self

    def add_history(self, entry: dict):
        self.state["history"].append({
            **entry,
            "timestamp": datetime.utcnow().isoformat(),
            "id": str(uuid.uuid4())[:8],
        })
        self.save()
        return self

    def get(self, key: str, default: Any = None) -> Any:
        return self.state.get(key, default)


class Agent:
    """Represents a single agent in the Mega Brain system."""

    def __init__(self, name: str, role: str, model: str, system_prompt: str):
        self.name = name
        self.role = role
        self.model = model
        self.system_prompt = system_prompt
        self.status = AgentStatus.IDLE

    def __repr__(self):
        return f"<Agent {self.name} ({self.role}) [{self.model}]>"


class Squad:
    """A squad of agents that work together on a task."""

    def __init__(self, name: str, agents: list[Agent]):
        self.name = name
        self.agents = {a.name: a for a in agents}

    def get(self, name: str) -> Optional[Agent]:
        return self.agents.get(name)

    def all(self) -> list[Agent]:
        return list(self.agents.values())

    def __repr__(self):
        return f"<Squad {self.name} ({len(self.agents)} agents)>"


class Orchestrator:
    """
    Mega Brain Orchestrator — the "JARVIS" of the system.
    
    Coordinates voice input, routing, squad activation, and
    dashboard updates through a unified pipeline.
    """

    def __init__(self, state_path: str = "state.json"):
        self.state = StateManager(state_path)
        self.squads: dict[str, Squad] = {}
        self.pipeline_steps: list[dict] = []

    def register_squad(self, squad: Squad):
        self.squads[squad.name] = squad
        for agent in squad.all():
            self.state.set_agent_status(agent.name, AgentStatus.IDLE)
        return self

    def register_pipeline(self, steps: list[dict]):
        self.pipeline_steps = steps
        return self

    async def run_pipeline(self, input_text: str, voice_input: bool = False) -> dict:
        """
        Main execution pipeline.
        
        1. Voice input processing
        2. Sentiment analysis & keyword detection
        3. Model routing
        4. Squad activation
        5. Agent execution
        6. Consolidation
        7. Dashboard update
        """
        session_id = str(uuid.uuid4())[:8]
        
        self.state.state["status"] = PipelineStatus.RUNNING.value
        self.state.set_pipeline_step("init", "running", {"session_id": session_id})
        self.state.add_history({
            "type": "session_start",
            "session_id": session_id,
            "input": input_text[:100],
            "voice": voice_input,
        })

        result = {
            "session_id": session_id,
            "input": input_text,
            "voice": voice_input,
            "steps": [],
            "output": None,
            "error": None,
        }

        for step in self.pipeline_steps:
            step_name = step.get("name", "unknown")
            step_handler = step.get("handler")
            
            self.state.set_pipeline_step(step_name, "running")
            
            try:
                if step_handler:
                    step_result = await step_handler(input_text, step)
                    result["steps"].append({
                        "step": step_name,
                        "status": "completed",
                        "output": step_result,
                    })
                else:
                    result["steps"].append({
                        "step": step_name,
                        "status": "skipped",
                    })
                    
                self.state.set_pipeline_step(step_name, "completed")
            except Exception as e:
                self.state.set_pipeline_step(step_name, "failed", {"error": str(e)})
                result["error"] = str(e)
                result["steps"].append({
                    "step": step_name,
                    "status": "failed",
                    "error": str(e),
                })
                break

        if result["error"]:
            self.state.state["status"] = PipelineStatus.FAILED.value
        else:
            self.state.state["status"] = PipelineStatus.COMPLETED.value
            
        self.state.add_history({
            "type": "session_end",
            "session_id": session_id,
            "status": "failed" if result["error"] else "completed",
            "steps_count": len(result["steps"]),
        })
        
        self.state.save()
        return result
