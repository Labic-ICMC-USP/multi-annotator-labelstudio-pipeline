from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import itertools
import json

import pandas as pd
import requests
from sklearn.metrics import cohen_kappa_score

BASE_URL = "http://127.0.0.1:8080"
API_TOKEN = "6fc6fd65c6d2b6927d94adb7867b39c5998f157b"

# Se quiser filtrar apenas seus projetos importados, use por exemplo:
# PROJECT_PREFIX = "ner_"
# Se quiser pegar tudo, deixe None
PROJECT_PREFIX: Optional[str] = None

OUTPUT_XLSX = "annotation_export_report.xlsx"
OUTPUT_JSON_SUMMARY = "annotation_export_summary.json"
OUTPUT_DEBUG_XLSX = "debug_projects.xlsx"

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


def safe_str(value: Any) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def parse_project_name(project_title: str) -> Tuple[str, str]:
    """
    Esperado:
    project_code__annotator_email
    """
    title = safe_str(project_title)
    if "__" in title:
        project_code, annotator_email = title.split("__", 1)
        return project_code.strip(), annotator_email.strip()
    return title, ""


def extract_spans_from_annotation(annotation: Dict[str, Any]) -> List[Dict[str, Any]]:
    spans: List[Dict[str, Any]] = []

    for result in annotation.get("result", []) or []:
        value = result.get("value", {}) or {}

        if "start" not in value or "end" not in value:
            continue

        labels = value.get("labels", [])
        if not labels:
            continue

        spans.append(
            {
                "from_name": result.get("from_name"),
                "to_name": result.get("to_name"),
                "type": result.get("type"),
                "start": value.get("start"),
                "end": value.get("end"),
                "text": value.get("text"),
                "label": labels[0],
            }
        )

    return spans


def choose_annotation(task: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    annotations = task.get("annotations", []) or []
    if not annotations:
        return None

    # tenta pegar a última anotação com algum resultado
    annotations_sorted = sorted(
        annotations,
        key=lambda a: safe_str(a.get("updated_at", "")) or safe_str(a.get("created_at", "")),
    )

    for ann in reversed(annotations_sorted):
        result = ann.get("result", []) or []
        if result:
            return ann

    # se não houver resultado, devolve a última mesmo
    return annotations_sorted[-1]


def build_export_tables(
    projects: List[Dict[str, Any]],
    client: LabelStudioClient,
    project_prefix: Optional[str] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    document_rows: List[Dict[str, Any]] = []
    span_rows: List[Dict[str, Any]] = []
    debug_rows: List[Dict[str, Any]] = []

    for project in projects:
        project_id = int(project["id"])
        project_name = safe_str(project.get("title", ""))

        if project_prefix and not project_name.startswith(project_prefix):
            continue

        project_code_from_name, annotator_email_from_name = parse_project_name(project_name)

        tasks = client.list_project_tasks(project_id)

        n_with_annotations = 0
        n_with_results = 0

        for task in tasks:
            annotations = task.get("annotations", []) or []
            if annotations:
                n_with_annotations += 1

            selected_annotation = choose_annotation(task)
            if selected_annotation and (selected_annotation.get("result", []) or []):
                n_with_results += 1

        debug_rows.append(
            {
                "project_id": project_id,
                "project_name": project_name,
                "n_tasks": len(tasks),
                "n_tasks_with_annotations": n_with_annotations,
                "n_tasks_with_results": n_with_results,
            }
        )

        print(
            f"[DEBUG] Project={project_name} | tasks={len(tasks)} | "
            f"with_annotations={n_with_annotations} | with_results={n_with_results}"
        )

        for task in tasks:
            task_data = task.get("data", {}) or {}
            selected_annotation = choose_annotation(task)

            if selected_annotation is None:
                continue

            project_code = safe_str(task_data.get("project_code", project_code_from_name))
            project_title = safe_str(task_data.get("project_title", ""))
            external_id = safe_str(task_data.get("external_id", ""))
            text = safe_str(task_data.get("text", ""))
            batch = safe_str(task_data.get("batch", ""))
            source = safe_str(task_data.get("source", ""))
            annotator_email = safe_str(
                task_data.get("assigned_annotator_email", annotator_email_from_name)
            )

            spans = extract_spans_from_annotation(selected_annotation)

            document_rows.append(
                {
                    "project_id": project_id,
                    "project_name": project_name,
                    "project_code": project_code,
                    "project_title": project_title,
                    "annotator_email": annotator_email,
                    "external_id": external_id,
                    "text": text,
                    "batch": batch,
                    "source": source,
                    "annotation_id": selected_annotation.get("id"),
                    "created_at": selected_annotation.get("created_at"),
                    "updated_at": selected_annotation.get("updated_at"),
                    "n_spans": len(spans),
                    "has_result": 1 if (selected_annotation.get("result", []) or []) else 0,
                }
            )

            for span in spans:
                span_rows.append(
                    {
                        "project_id": project_id,
                        "project_name": project_name,
                        "project_code": project_code,
                        "project_title": project_title,
                        "annotator_email": annotator_email,
                        "external_id": external_id,
                        "batch": batch,
                        "source": source,
                        "annotation_id": selected_annotation.get("id"),
                        "span_start": span["start"],
                        "span_end": span["end"],
                        "span_text": span["text"],
                        "label": span["label"],
                        "text_full": text,
                    }
                )

    df_documents = pd.DataFrame(document_rows)
    df_spans = pd.DataFrame(span_rows)
    df_debug = pd.DataFrame(debug_rows)

    return df_documents, df_spans, df_debug


def build_label_presence(df_documents: pd.DataFrame, df_spans: pd.DataFrame) -> pd.DataFrame:
    if df_documents.empty or df_spans.empty:
        return pd.DataFrame(
            columns=[
                "project_code",
                "project_title",
                "external_id",
                "annotator_email",
                "label",
                "present",
            ]
        )

    base_docs = (
        df_documents[
            ["project_code", "project_title", "external_id", "annotator_email"]
        ]
        .drop_duplicates()
        .copy()
    )

    all_labels = sorted(df_spans["label"].dropna().astype(str).unique().tolist())

    grouped = (
        df_spans.groupby(
            ["project_code", "project_title", "external_id", "annotator_email"],
            dropna=False,
        )["label"]
        .apply(lambda s: set(s.astype(str)))
        .reset_index(name="label_set")
    )

    merged = base_docs.merge(
        grouped,
        on=["project_code", "project_title", "external_id", "annotator_email"],
        how="left",
    )

    merged["label_set"] = merged["label_set"].apply(
        lambda x: x if isinstance(x, set) else set()
    )

    rows: List[Dict[str, Any]] = []
    for _, row in merged.iterrows():
        for label in all_labels:
            rows.append(
                {
                    "project_code": row["project_code"],
                    "project_title": row["project_title"],
                    "external_id": row["external_id"],
                    "annotator_email": row["annotator_email"],
                    "label": label,
                    "present": 1 if label in row["label_set"] else 0,
                }
            )

    return pd.DataFrame(rows)


def build_user_stats(df_documents: pd.DataFrame, df_spans: pd.DataFrame) -> pd.DataFrame:
    if df_documents.empty:
        return pd.DataFrame(
            columns=[
                "project_code",
                "project_title",
                "annotator_email",
                "n_documents",
                "n_annotations",
                "n_tasks",
                "n_spans",
                "avg_spans_per_document",
            ]
        )

    doc_stats = (
        df_documents.groupby(["project_code", "project_title", "annotator_email"], dropna=False)
        .agg(
            n_documents=("external_id", "nunique"),
            n_annotations=("annotation_id", "nunique"),
            n_tasks=("external_id", "count"),
        )
        .reset_index()
    )

    if df_spans.empty:
        doc_stats["n_spans"] = 0
        doc_stats["avg_spans_per_document"] = 0.0
        return doc_stats

    span_stats = (
        df_spans.groupby(["project_code", "project_title", "annotator_email"], dropna=False)
        .agg(n_spans=("label", "count"))
        .reset_index()
    )

    stats = doc_stats.merge(
        span_stats,
        on=["project_code", "project_title", "annotator_email"],
        how="left",
    )
    stats["n_spans"] = stats["n_spans"].fillna(0).astype(int)
    stats["avg_spans_per_document"] = stats["n_spans"] / stats["n_documents"].replace(0, 1)

    return stats


def build_label_stats(df_spans: pd.DataFrame) -> pd.DataFrame:
    if df_spans.empty:
        return pd.DataFrame(
            columns=[
                "project_code",
                "project_title",
                "annotator_email",
                "label",
                "n_spans",
                "n_documents",
            ]
        )

    return (
        df_spans.groupby(["project_code", "project_title", "annotator_email", "label"], dropna=False)
        .agg(
            n_spans=("label", "count"),
            n_documents=("external_id", "nunique"),
        )
        .reset_index()
        .sort_values(["project_code", "annotator_email", "label"])
        .reset_index(drop=True)
    )


def compute_pairwise_kappa(df_presence: pd.DataFrame) -> pd.DataFrame:
    if df_presence.empty:
        return pd.DataFrame(
            columns=[
                "project_code",
                "project_title",
                "annotator_a",
                "annotator_b",
                "label",
                "n_docs_overlap",
                "cohen_kappa",
                "agreement_rate",
            ]
        )

    rows: List[Dict[str, Any]] = []

    grouped = df_presence.groupby(["project_code", "project_title", "label"], dropna=False)

    for (project_code, project_title, label), df_label in grouped:
        pivot = df_label.pivot_table(
            index="external_id",
            columns="annotator_email",
            values="present",
            aggfunc="max",
        )

        annotators = sorted([safe_str(c) for c in pivot.columns.tolist()])

        for annotator_a, annotator_b in itertools.combinations(annotators, 2):
            pair = pivot[[annotator_a, annotator_b]].dropna()
            n_docs_overlap = len(pair)

            if n_docs_overlap == 0:
                kappa = None
                agreement_rate = None
            else:
                y1 = pair[annotator_a].astype(int)
                y2 = pair[annotator_b].astype(int)
                kappa = float(cohen_kappa_score(y1, y2))
                agreement_rate = float((y1 == y2).mean())

            rows.append(
                {
                    "project_code": project_code,
                    "project_title": project_title,
                    "annotator_a": annotator_a,
                    "annotator_b": annotator_b,
                    "label": label,
                    "n_docs_overlap": n_docs_overlap,
                    "cohen_kappa": kappa,
                    "agreement_rate": agreement_rate,
                }
            )

    return pd.DataFrame(rows)


def compute_pairwise_kappa_summary(df_pairwise_kappa: pd.DataFrame) -> pd.DataFrame:
    if df_pairwise_kappa.empty:
        return pd.DataFrame(
            columns=[
                "project_code",
                "project_title",
                "annotator_a",
                "annotator_b",
                "macro_kappa_mean",
                "macro_agreement_mean",
                "n_labels",
            ]
        )

    return (
        df_pairwise_kappa.groupby(
            ["project_code", "project_title", "annotator_a", "annotator_b"],
            dropna=False,
        )
        .agg(
            macro_kappa_mean=("cohen_kappa", "mean"),
            macro_agreement_mean=("agreement_rate", "mean"),
            n_labels=("label", "nunique"),
        )
        .reset_index()
    )


def save_excel_report(
    output_path: str,
    df_documents: pd.DataFrame,
    df_spans: pd.DataFrame,
    df_presence: pd.DataFrame,
    df_user_stats: pd.DataFrame,
    df_label_stats: pd.DataFrame,
    df_pairwise_kappa: pd.DataFrame,
    df_pairwise_summary: pd.DataFrame,
) -> None:
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        df_documents.to_excel(writer, sheet_name="documents", index=False)
        df_spans.to_excel(writer, sheet_name="spans", index=False)
        df_presence.to_excel(writer, sheet_name="label_presence", index=False)
        df_user_stats.to_excel(writer, sheet_name="user_stats", index=False)
        df_label_stats.to_excel(writer, sheet_name="label_stats", index=False)
        df_pairwise_kappa.to_excel(writer, sheet_name="pairwise_kappa", index=False)
        df_pairwise_summary.to_excel(writer, sheet_name="pairwise_kappa_summary", index=False)


def save_debug_excel(output_path: str, df_debug: pd.DataFrame) -> None:
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        df_debug.to_excel(writer, sheet_name="projects_debug", index=False)


def save_json_summary(
    output_path: str,
    df_documents: pd.DataFrame,
    df_spans: pd.DataFrame,
    df_user_stats: pd.DataFrame,
    df_pairwise_kappa: pd.DataFrame,
) -> None:
    summary = {
        "n_projects_with_annotations": int(df_documents["project_name"].nunique()) if not df_documents.empty else 0,
        "n_documents_annotated": int(df_documents["external_id"].nunique()) if not df_documents.empty else 0,
        "n_annotations": int(df_documents["annotation_id"].nunique()) if not df_documents.empty else 0,
        "n_spans": int(len(df_spans)),
        "n_annotators": int(df_user_stats["annotator_email"].nunique()) if not df_user_stats.empty else 0,
        "n_pairwise_kappa_rows": int(len(df_pairwise_kappa)),
    }

    Path(output_path).write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    if API_TOKEN == "PUT_YOUR_TOKEN_HERE":
        raise ValueError("Please update API_TOKEN in the script before running it.")

    client = LabelStudioClient(BASE_URL, API_TOKEN)

    print("[INFO] Listing projects...")
    projects = client.list_projects()
    print(f"[OK] Found {len(projects)} projects in total.")

    print("[INFO] Exporting annotations...")
    df_documents, df_spans, df_debug = build_export_tables(
        projects=projects,
        client=client,
        project_prefix=PROJECT_PREFIX,
    )

    print(f"[OK] Documents exported: {len(df_documents)}")
    print(f"[OK] Spans exported: {len(df_spans)}")

    print("[INFO] Building label presence...")
    df_presence = build_label_presence(df_documents, df_spans)

    print("[INFO] Building user statistics...")
    df_user_stats = build_user_stats(df_documents, df_spans)

    print("[INFO] Building label statistics...")
    df_label_stats = build_label_stats(df_spans)

    print("[INFO] Computing pairwise kappa...")
    df_pairwise_kappa = compute_pairwise_kappa(df_presence)

    print("[INFO] Computing pairwise kappa summary...")
    df_pairwise_summary = compute_pairwise_kappa_summary(df_pairwise_kappa)

    print("[INFO] Writing Excel report...")
    save_excel_report(
        output_path=OUTPUT_XLSX,
        df_documents=df_documents,
        df_spans=df_spans,
        df_presence=df_presence,
        df_user_stats=df_user_stats,
        df_label_stats=df_label_stats,
        df_pairwise_kappa=df_pairwise_kappa,
        df_pairwise_summary=df_pairwise_summary,
    )

    print("[INFO] Writing debug workbook...")
    save_debug_excel(OUTPUT_DEBUG_XLSX, df_debug)

    print("[INFO] Writing JSON summary...")
    save_json_summary(
        output_path=OUTPUT_JSON_SUMMARY,
        df_documents=df_documents,
        df_spans=df_spans,
        df_user_stats=df_user_stats,
        df_pairwise_kappa=df_pairwise_kappa,
    )

    print(f"[DONE] Excel report written to: {OUTPUT_XLSX}")
    print(f"[DONE] Debug workbook written to: {OUTPUT_DEBUG_XLSX}")
    print(f"[DONE] JSON summary written to: {OUTPUT_JSON_SUMMARY}")


if __name__ == "__main__":
    main()
