import uuid
from typing import Dict, List

# The new job structure will include a list of sub-steps
# { 
#   "job_id_1": {
#     "status": "running", 
#     "main_progress": "Processing page 1/20",
#     "sub_steps": [
#       {"name": "Extracting Text", "status": "completed"},
#       {"name": "Chunking Content", "status": "running"},
#       ...
#     ]
#   }, ... 
# }
_jobs: Dict[str, Dict] = {}

def create_job() -> str:
    """Creates a new job and returns its ID."""
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {
        "status": "pending", 
        "main_progress": "Initializing...",
        "sub_steps": []
    }
    return job_id

def get_job_status(job_id: str) -> Dict | None:
    """Gets the status of a specific job."""
    return _jobs.get(job_id)

def update_job_status(job_id: str, status: str, main_progress: str = "", sub_steps: List[Dict] = None):
    """Updates the main status and progress of a job, and can reset sub-steps."""
    if job_id in _jobs:
        job = _jobs[job_id]
        job["status"] = status
        if main_progress:
            job["main_progress"] = main_progress
        if sub_steps is not None: # Allows resetting the steps for a new page
            job["sub_steps"] = sub_steps

def update_job_sub_step(job_id: str, step_name: str, step_status: str, detail: str = ""):
    """Updates the status and detail of a specific sub-step for a job."""
    if job_id in _jobs:
        job = _jobs[job_id]
        for step in job["sub_steps"]:
            if step["name"] == step_name:
                step["status"] = step_status
                step["detail"] = detail # <-- Add the detail string
                break

def get_all_jobs():
    """Returns all jobs."""
    return _jobs