from __future__ import annotations
from .models import Task

class TaskPlanner:
    PHASES=("observe","classify","research","plan","gate","execute","test","evidence","learn")

    def plan(self, task: Task) -> dict:
        return {
            "task_id":task.task_id,
            "title":task.title,
            "phases":[
                {"phase":"observe","mutation":False},
                {"phase":"classify","mutation":False},
                {"phase":"research","mutation":False},
                {"phase":"plan","mutation":False},
                {"phase":"gate","mutation":False},
                {"phase":"execute","mutation":True,"locked_in_v1":True},
                {"phase":"test","mutation":False},
                {"phase":"evidence","mutation":False},
                {"phase":"learn","mutation":False},
            ],
            "rollback":"git restore only exact allowlisted paths; no force reset",
        }
