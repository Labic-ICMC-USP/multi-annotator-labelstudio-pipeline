from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
import json

import requests

BASE_URL = "http://127.0.0.1:8080"
API_TOKEN = "6fc6fd65c6d2b6927d94adb7867b39c5998f157b"

OUTPUT_JSON = "labelstudio_annotated_export.json"
OUTPUT_SUMMARY_JSON = "labelstudio_annotated_export_summary.json"

TIMEOUT = 60


class LabelStudioClient:
    def __init__(self, base_url: str, api_token: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Token {api_token}",
                "Content-Type": "application/json",
            }
        )

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def list_projects(self) -> List[Dict[str, Any]]:
        response = self.session.get(self._url("/api/projects/"), timeout=TIMEOUT)
        response.raise_for_status()
        data = response.json()

        if isinstance(data, dict) and "results" in data:
            return data["results"]
        if isinstance(data, list):
            return data
        return []

    def list_project_tasks(self, project_id: int) -> List[Dict[str, Any]]:
        url = self._url("/api/tasks/")
        params = {"project": project_id, "page_size": 100}
        items: List[Dict[str, Any]] = []

        while True:
            response = self.session.get(url, params=params, timeout=TIMEOUT)
            response.raise_for_status()
            data = response.json()

            if isinstance(data, dict) and "results" in data:
                items.extend(data["results"])
                next_url = data.get("next")
                if not next_url:
                    break
                url = next_url
                params = None
            elif isinstance(data, list):
                items.extend(data)
                break
            else:
                break

        return items


def has_annotations(task: Dict[str, Any]) -> bool:
    annotations = task.get("annotations", []) or []
    return len(annotations) > 0


def main() -> None:
    if API_TOKEN == "PUT_YOUR_TOKEN_HERE":
        raise ValueError("Please update API_TOKEN in the script before running it.")

    client = LabelStudioClient(BASE_URL, API_TOKEN)

    print("[INFO] Listing projects...")
    projects = client.list_projects()
    print(f"[OK] Found {len(projects)} projects.")

    export_data: List[Dict[str, Any]] = []
    summary_rows: List[Dict[str, Any]] = []

    total_tasks = 0
    total_tasks_with_annotations = 0

    for project in projects:
        project_id = int(project["id"])
        project_title = str(project.get("title", ""))

        print(f"[INFO] Reading project {project_id}: {project_title}")
        tasks = client.list_project_tasks(project_id)

        n_tasks = len(tasks)
        n_tasks_with_annotations = 0

        annotated_tasks: List[Dict[str, Any]] = []
        for task in tasks:
            if has_annotations(task):
                annotated_tasks.append(task)
                n_tasks_with_annotations += 1

        total_tasks += n_tasks
        total_tasks_with_annotations += n_tasks_with_annotations

        summary_rows.append(
            {
                "project_id": project_id,
                "project_title": project_title,
                "n_tasks": n_tasks,
                "n_tasks_with_annotations": n_tasks_with_annotations,
            }
        )

        export_data.append(
            {
                "project": {
                    "id": project_id,
                    "title": project_title,
                    "raw": project,
                },
                "annotated_tasks": annotated_tasks,
            }
        )

        print(
            f"[OK] Project {project_id}: tasks={n_tasks}, "
            f"annotated_tasks={n_tasks_with_annotations}"
        )

    Path(OUTPUT_JSON).write_text(
        json.dumps(export_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    summary = {
        "n_projects": len(projects),
        "n_total_tasks": total_tasks,
        "n_total_tasks_with_annotations": total_tasks_with_annotations,
        "projects": summary_rows,
    }

    Path(OUTPUT_SUMMARY_JSON).write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"[DONE] Full JSON export written to: {OUTPUT_JSON}")
    print(f"[DONE] Summary JSON written to: {OUTPUT_SUMMARY_JSON}")


if __name__ == "__main__":
    main()
