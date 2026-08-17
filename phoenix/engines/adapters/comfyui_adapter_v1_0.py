"""Phoenix ComfyUI adapter foundation v1.0."""
from __future__ import annotations
import json,urllib.request
from pathlib import Path
from phoenix.engines.visual_engine_discovery_v1_0 import discover_comfyui
VERSION="1.0.0"
def capability_state(repository:Path)->dict:
    d=discover_comfyui(repository)
    return {**d,"adapter_version":VERSION,"capabilities":["AI_IMAGE","AI_IMAGE_TO_IMAGE","AI_CONCEPT_VARIANTS","AI_VIDEO"]}
def queue_prompt(repository:Path,workflow:dict,timeout:float=10.0)->dict:
    state=capability_state(repository)
    if not state.get("api_available"):raise RuntimeError("COMFYUI_API_NOT_AVAILABLE")
    body=json.dumps({"prompt":workflow}).encode("utf-8")
    req=urllib.request.Request(state["url"]+"/prompt",data=body,headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=timeout) as r:
        data=json.loads(r.read().decode("utf-8"))
    return {"engine":"comfyui","adapter_version":VERSION,"queued":True,"response":data}
