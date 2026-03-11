from celery import Celery
from supervisor import Supervisor
import requests
import os

app = Celery(
    "deepcontext_worker",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0",
)

app.conf.update(
    task_track_started=True,
    result_expires=3600
)

@app.task(name="process_document_task")
def process_document_task(file_source: str, user_dept: str, is_slack_upload: bool = False, slack_token: str = None):

    if is_slack_upload:
        # Use a proper filename (sanitize it!)
        file_name = file_source.split('/')[-1]
        local_path = os.path.join("./data", f"slack_{file_name}")
        
        # Download with Authorization Header
        headers = {"Authorization": f"Bearer {slack_token}"}
        response = requests.get(file_source, headers=headers, stream=True)
        
        if response.status_code == 200:
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            file_to_process = local_path
        else:
            print(f"❌ Failed to download from Slack. Status: {response.status_code}")
            return "Download Failed"
    else:
        file_to_process = file_source

    supervisor = Supervisor()
    supervisor.supervisor(file_to_process, user_dept)
    return "Ingestion Complete"