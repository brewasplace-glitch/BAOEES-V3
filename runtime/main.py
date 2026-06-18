from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="BREWSTER ENGINEERING WIZARD API")

class ProjectRequest(BaseModel):
    project_name: str
    project_type: str
    location: str | None = None
    country: str | None = None
    description: str | None = None

@app.get("/")
def root():
    return {"status": "BREWSTER ENGINEERING WIZARD runtime actief"}

@app.post("/projects/create")
def create_project(request: ProjectRequest):
    return {
        "message": "Project aangemaakt",
        "project": request.model_dump(),
        "next_step": "ADAE -> AAIE -> GECE -> Living Digital Twin",
    }
