from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
import shlex

import pandas as pd
import requests

BASE_URL = "http://127.0.0.1:8080"
API_TOKEN = "6fc6fd65c6d2b6927d94adb7867b39c5998f157b"
WORKBOOK_PATH = "annotation_workbook.xlsx"
LABEL_CONFIG_FILE = "label_config_ner.xml"

TIMEOUT = 60
IMPORT_BATCH_SIZE = 200
RESET_PASSWORDS_SCRIPT = "reset_passwords.sh"
LABEL_STUDIO_CONTAINER_NAME = "labelstudio_app"


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

    def list_users(self) -> List[Dict[str, Any]]:
        response = self.session.get(self._url("/api/users/"), timeout=TIMEOUT)
        response.raise_for_status()
        data = response.json()

        if isinstance(data, dict) and "results" in data:
            return data["results"]
        if isinstance(data, list):
            return data
        return []

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        email_norm = email.strip().lower()

        for user in self.list_users():
            user_email = str(user.get("email", "")).strip().lower()
            username = str(user.get("username", "")).strip().lower()

            if user_email == email_norm or username == email_norm:
                return user

        return None

    def update_user_basic_fields(
        self,
        user_id: int,
        email: str,
        first_name: str = "",
        last_name: str = "",
    ) -> bool:
        payload = {
            "username": email,
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
        }

        response = self.session.patch(
            self._url(f"/api/users/{user_id}/"),
            json=payload,
            timeout=TIMEOUT,
        )
        if response.status_code in (200, 201):
            return True

        response = self.session.put(
            self._url(f"/api/users/{user_id}/"),
            json=payload,
            timeout=TIMEOUT,
        )
        if response.status_code in (200, 201):
            return True

        print(
            f"[WARN] Could not update existing user fields for {email}. "
            f"Status={response.status_code} Body={response.text}"
        )
        return False

    def create_user(
        self,
        email: str,
        password: str,
        first_name: str = "",
        last_name: str = "",
    ) -> Dict[str, Any]:
        payload = {
            "username": email,
            "email": email,
            "password": password,
            "first_name": first_name,
            "last_name": last_name,
        }

        response = self.session.post(
            self._url("/api/users/"),
            json=payload,
            timeout=TIMEOUT,
        )

        if response.status_code in (200, 201):
            return response.json()

        if response.status_code in (400, 409):
            existing_user = self.get_user_by_email(email)
            if existing_user is not None:
                user_id = int(existing_user["id"])
                updated = self.update_user_basic_fields(
                    user_id=user_id,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                )

                if updated:
                    print(f"[USER] Existing user found. Basic fields updated: {email}")
                else:
                    print(f"[USER] Existing user found. Keeping existing data: {email}")

                return existing_user

        raise RuntimeError(
            f"Could not create user {email}: {response.status_code} {response.text}"
        )

    def list_projects(self) -> List[Dict[str, Any]]:
        response = self.session.get(self._url("/api/projects/"), timeout=TIMEOUT)
        response.raise_for_status()
        data = response.json()

        if isinstance(data, dict) and "results" in data:
            return data["results"]
        if isinstance(data, list):
            return data
        return []

    def get_project_by_title(self, title: str) -> Optional[Dict[str, Any]]:
        for project in self.list_projects():
            if str(project.get("title", "")).strip() == title.strip():
                return project
        return None

    def create_project(self, title: str, label_config: str) -> Dict[str, Any]:
        payload = {
            "title": title,
            "label_config": label_config,
        }

        response = self.session.post(
            self._url("/api/projects/"),
            json=payload,
            timeout=TIMEOUT,
        )

        if response.status_code in (200, 201):
            return response.json()

        raise RuntimeError(
            f"Could not create project '{title}': "
            f"{response.status_code} {response.text}"
        )

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

    def import_tasks(self, project_id: int, tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        response = self.session.post(
            self._url(f"/api/projects/{project_id}/import"),
            json=tasks,
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        return response.json()


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(col).strip() for col in df.columns]
    return df


def safe_str(value: Any) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def read_workbook(workbook_path: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    workbook = pd.ExcelFile(workbook_path)

    df_users = workbook.parse("users")
    df_tasks = workbook.parse("tasks")

    df_users = normalize_columns(df_users).fillna("")
    df_tasks = normalize_columns(df_tasks).fillna("")

    return df_users, df_tasks


def validate_users_sheet(df_users: pd.DataFrame) -> None:
    required_columns = {"email", "password"}
    missing = required_columns - set(df_users.columns)

    if missing:
        raise ValueError(
            f"Missing required columns in 'users' sheet: {sorted(missing)}"
        )


def validate_tasks_sheet(df_tasks: pd.DataFrame) -> None:
    required_columns = {
        "project_code",
        "project_title",
        "external_id",
        "text",
    }
    missing = required_columns - set(df_tasks.columns)

    if missing:
        raise ValueError(
            f"Missing required columns in 'tasks' sheet: {sorted(missing)}"
        )

    annotator_columns = [col for col in df_tasks.columns if col.startswith("annotator_")]
    if not annotator_columns:
        raise ValueError(
            "The 'tasks' sheet must contain at least one annotator column, "
            "such as annotator_1, annotator_2, or annotator_3."
        )


def chunked(items: List[Dict[str, Any]], size: int) -> List[List[Dict[str, Any]]]:
    return [items[i:i + size] for i in range(0, len(items), size)]


def build_project_name(project_code: str, annotator_email: str, max_len: int = 50) -> str:
    name = f"{project_code}__{annotator_email}"
    if len(name) <= max_len:
        return name
    return name[:max_len]


def build_task_payload(row: pd.Series, annotator_email: str) -> Dict[str, Any]:
    data = {
        "project_code": safe_str(row.get("project_code", "")),
        "project_title": safe_str(row.get("project_title", "")),
        "external_id": safe_str(row.get("external_id", "")),
        "text": safe_str(row.get("text", "")),
        "assigned_annotator_email": annotator_email,
    }

    for optional_col in ["batch", "source"]:
        if optional_col in row.index:
            data[optional_col] = safe_str(row.get(optional_col, ""))

    return {"data": data}


def get_existing_external_ids(client: LabelStudioClient, project_id: int) -> set[str]:
    tasks = client.list_project_tasks(project_id)
    existing_ids: set[str] = set()

    for task in tasks:
        task_data = task.get("data", {}) or {}
        external_id = task_data.get("external_id")
        if external_id is not None:
            existing_ids.add(str(external_id).strip())

    return existing_ids


def generate_reset_passwords_script(
    df_users: pd.DataFrame,
    output_path: str = RESET_PASSWORDS_SCRIPT,
    container_name: str = LABEL_STUDIO_CONTAINER_NAME,
) -> None:
    lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "",
        f'CONTAINER_NAME="{container_name}"',
        "",
    ]

    for _, row in df_users.iterrows():
        email = safe_str(row.get("email", ""))
        password = safe_str(row.get("password", ""))

        if not email or not password:
            continue

        email_quoted = shlex.quote(email)
        password_quoted = shlex.quote(password)

        lines.append(
            f'docker exec "$CONTAINER_NAME" '
            f'label-studio reset_password --username {email_quoted} --password {password_quoted}'
        )

    Path(output_path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    if API_TOKEN == "PUT_YOUR_TOKEN_HERE":
        raise ValueError("Please update API_TOKEN in the script before running it.")

    label_config = Path(LABEL_CONFIG_FILE).read_text(encoding="utf-8")

    df_users, df_tasks = read_workbook(WORKBOOK_PATH)

    validate_users_sheet(df_users)
    validate_tasks_sheet(df_tasks)

    generate_reset_passwords_script(
        df_users=df_users,
        output_path=RESET_PASSWORDS_SCRIPT,
        container_name=LABEL_STUDIO_CONTAINER_NAME,
    )
    print(f"[OK] Generated {RESET_PASSWORDS_SCRIPT}")

    client = LabelStudioClient(BASE_URL, API_TOKEN)

    print("[INFO] Creating or updating users...")
    for _, row in df_users.iterrows():
        email = safe_str(row.get("email", ""))
        password = safe_str(row.get("password", ""))
        first_name = safe_str(row.get("first_name", ""))
        last_name = safe_str(row.get("last_name", ""))

        if not email:
            continue

        if not password:
            print(f"[WARN] Skipping user without password: {email}")
            continue

        client.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )
        print(f"[OK] User ready: {email}")

    annotator_columns = [col for col in df_tasks.columns if col.startswith("annotator_")]

    print("[INFO] Creating projects and importing tasks...")
    for annotator_col in annotator_columns:
        annotator_emails = sorted(
            {
                safe_str(value)
                for value in df_tasks[annotator_col].tolist()
                if safe_str(value)
            }
        )

        for annotator_email in annotator_emails:
            assigned_rows = df_tasks[
                df_tasks[annotator_col].apply(safe_str).str.lower() == annotator_email.lower()
            ].copy()

            if assigned_rows.empty:
                continue

            grouped = assigned_rows.groupby(["project_code", "project_title"], dropna=False)

            for (project_code, project_title), df_group in grouped:
                project_code = safe_str(project_code)
                project_title = safe_str(project_title)

                project_name = build_project_name(project_code, annotator_email)

                project = client.get_project_by_title(project_name)
                if project is None:
                    project = client.create_project(project_name, label_config)
                    print(f"[OK] Project created: {project_name}")
                else:
                    print(f"[INFO] Project already exists: {project_name}")

                project_id = int(project["id"])
                existing_external_ids = get_existing_external_ids(client, project_id)

                tasks_payload: List[Dict[str, Any]] = []
                for _, row in df_group.iterrows():
                    external_id = safe_str(row.get("external_id", ""))
                    if not external_id:
                        continue
                    if external_id in existing_external_ids:
                        continue

                    tasks_payload.append(build_task_payload(row, annotator_email))

                if not tasks_payload:
                    print(f"[INFO] No new tasks to import for project: {project_name}")
                    continue

                for batch in chunked(tasks_payload, IMPORT_BATCH_SIZE):
                    result = client.import_tasks(project_id, batch)
                    print(
                        f"[OK] Imported {len(batch)} tasks into {project_name}. "
                        f"Response: {result}"
                    )

    print("[DONE] Import process completed successfully.")
    print(f"[NEXT] Run: chmod +x {RESET_PASSWORDS_SCRIPT} && ./{RESET_PASSWORDS_SCRIPT}")


if __name__ == "__main__":
    main()
