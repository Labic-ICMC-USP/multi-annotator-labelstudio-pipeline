from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

BASE_URL = "http://127.0.0.1:8080"
API_TOKEN = "6fc6fd65c6d2b6927d94adb7867b39c5998f157b"
TIMEOUT = 120
PAGE_SIZE = 100
OUTPUT_JSON = "all_annotations_export.json"


class LabelStudioClient:
    def __init__(self, base_url: str, api_token: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Token {api_token}"})

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def list_projects(self) -> List[Dict[str, Any]]:
        url = self._url("/api/projects/")
        params = {"page_size": PAGE_SIZE}
        items: List[Dict[str, Any]] = []

        while True:
            response = self.session.get(url, params=params, timeout=TIMEOUT)
            response.raise_for_status()
            data = response.json()

            if isinstance(data, list):
                items.extend(data)
                break

            if isinstance(data, dict) and "results" in data:
                items.extend(data["results"])
                next_url = data.get("next")
                if not next_url:
                    break
                url = next_url
                params = None
                continue

            raise RuntimeError(f"Unexpected response while listing projects: {type(data)}")

        return items

    def export_project_annotations(self, project_id: int) -> List[Dict[str, Any]]:
        response = self.session.get(
            self._url(f"/api/projects/{project_id}/export"),
            params={"exportType": "JSON"},
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()

        if not isinstance(data, list):
            raise RuntimeError(
                f"Unexpected export payload for project {project_id}: {type(data)}"
            )

        return data


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def project_matches(project: Dict[str, Any], project_filter: Optional[str]) -> bool:
    if not project_filter:
        return True

    title = normalize_text(project.get("title"))
    return project_filter.lower() in title.lower()


def has_annotation_content(task: Dict[str, Any]) -> bool:
    annotations = task.get("annotations") or []
    if not annotations:
        return False

    for ann in annotations:
        if ann.get("result"):
            return True
        if ann.get("was_cancelled"):
            return True

    return True


def build_combined_export(
    projects: List[Dict[str, Any]],
    client: LabelStudioClient,
    project_filter: Optional[str],
) -> Dict[str, Any]:
    exported_projects: List[Dict[str, Any]] = []

    for project in projects:
        project_id = int(project["id"])
        project_title = normalize_text(project.get("title"))

        if not project_matches(project, project_filter):
            continue

        print(f"[INFO] Exporting project {project_id}: {project_title}")
        tasks = client.export_project_annotations(project_id)

        annotated_tasks = [task for task in tasks if has_annotation_content(task)]

        print(
            f"[OK] project_id={project_id} total_exported={len(tasks)} "
            f"annotated_or_skipped={len(annotated_tasks)}"
        )

        exported_projects.append(
            {
                "project": {
                    "id": project_id,
                    "title": project_title,
                    "task_number": project.get("task_number"),
                    "num_tasks_with_annotations": project.get("num_tasks_with_annotations"),
                    "total_annotations_number": project.get("total_annotations_number"),
                },
                "tasks": annotated_tasks,
            }
        )

    return {
        "base_url": client.base_url,
        "project_filter": project_filter,
        "n_projects": len(exported_projects),
        "projects": exported_projects,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export all annotated tasks from all Label Studio projects to one JSON file."
    )
    parser.add_argument(
        "--base-url",
        default=BASE_URL,
        help="Label Studio base URL. Default: %(default)s",
    )
    parser.add_argument(
        "--api-token",
        default=API_TOKEN,
        help="Label Studio API token. Default comes from the script constant.",
    )
    parser.add_argument(
        "--project-filter",
        default=None,
        help="Case-insensitive substring filter for project title.",
    )
    parser.add_argument(
        "--output",
        default=OUTPUT_JSON,
        help="Output JSON file. Default: %(default)s",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.api_token == "PUT_YOUR_TOKEN_HERE":
        raise ValueError("Update API_TOKEN in the script or pass --api-token.")

    client = LabelStudioClient(base_url=args.base_url, api_token=args.api_token)

    print("[INFO] Listing projects...")
    projects = client.list_projects()
    print(f"[OK] Found {len(projects)} projects.")

    combined = build_combined_export(
        projects=projects,
        client=client,
        project_filter=args.project_filter,
    )

    output_path = Path(args.output)
    output_path.write_text(
        json.dumps(combined, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"[DONE] JSON written to: {output_path}")


if __name__ == "__main__":
    main()
