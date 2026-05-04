from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import httpx


# Prepare a PaperPilot project for RAG integration evaluation without using the frontend.
#
# Usage:
#     python eval/prepare_eval_project.py --api-url http://localhost:8000 --papers-dir paper
#
# Then run the actual RAG evaluation:
#     python eval/run_rag_eval.py --project-id <PROJECT_ID> --api-url http://localhost:8000
#
# This script calls the local FastAPI backend directly. It creates a project, uploads PDF files,
# and waits until each document has parse_status=parsed and index_status=indexed.
# The default papers directory is paper. You can override it with --papers-dir.


DEFAULT_API_URL = "http://localhost:8000"
DEFAULT_PAPERS_DIR = Path("paper")
DEFAULT_DOCUMENTS_MAP = Path("eval/rag_eval_documents.json")
DEFAULT_PROJECT_NAME = "rag-eval-project"


def normalize_api_url(api_url: str) -> str:
    return api_url.rstrip("/")


def find_pdfs(papers_dir: Path) -> list[Path]:
    if not papers_dir.exists():
        raise FileNotFoundError(
            f"PDF directory does not exist: {papers_dir}. "
            f"当前默认目录是 {DEFAULT_PAPERS_DIR.as_posix()}；也可以通过 --papers-dir 指定目录。"
        )
    if not papers_dir.is_dir():
        raise NotADirectoryError(f"PDF path is not a directory: {papers_dir}")

    pdfs = sorted(path for path in papers_dir.glob("*.pdf") if path.is_file())
    if not pdfs:
        raise FileNotFoundError(f"No PDF files found in: {papers_dir}")
    return pdfs


def create_project(client: httpx.Client, api_url: str, project_name: str) -> str:
    payload = {
        "title": project_name,
        "research_direction": "RAG evaluation",
        "keywords": ["RAG", "evaluation", "PaperPilot"],
        "description": "Project created by eval/prepare_eval_project.py for local RAG integration evaluation.",
    }
    response = client.post(f"{api_url}/api/projects", json=payload)
    response.raise_for_status()
    project = response.json()
    project_id = project.get("id")
    if not project_id:
        raise RuntimeError(f"Create project response did not include id: {project}")
    return str(project_id)


def upload_pdf(client: httpx.Client, api_url: str, project_id: str, pdf_path: Path) -> dict[str, Any]:
    with pdf_path.open("rb") as file:
        response = client.post(
            f"{api_url}/api/projects/{project_id}/documents/upload",
            files={"file": (pdf_path.name, file, "application/pdf")},
        )
    response.raise_for_status()
    upload_result = response.json()
    document_id = upload_result.get("document_id")
    if not document_id:
        raise RuntimeError(f"Upload response did not include document_id for {pdf_path.name}: {upload_result}")
    return upload_result


def write_documents_map(path: Path, project_id: str, documents: dict[str, dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "project_id": project_id,
        "documents": documents,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def get_document(client: httpx.Client, api_url: str, document_id: str) -> dict[str, Any]:
    response = client.get(f"{api_url}/api/documents/{document_id}")
    response.raise_for_status()
    return response.json()


def get_task(client: httpx.Client, api_url: str, task_id: str | None) -> dict[str, Any] | None:
    if not task_id:
        return None
    response = client.get(f"{api_url}/api/tasks/{task_id}")
    response.raise_for_status()
    return response.json()


def is_document_ready(document: dict[str, Any]) -> bool:
    return document.get("parse_status") == "parsed" and document.get("index_status") == "indexed"


def assert_document_not_failed(document: dict[str, Any]) -> None:
    parse_status = document.get("parse_status")
    index_status = document.get("index_status")
    if parse_status == "failed":
        message = document.get("error_message") or "unknown parse error"
        raise RuntimeError(f"Document parse failed for {document.get('original_filename')}: {message}")
    if index_status == "failed":
        message = document.get("index_error_message") or "unknown index error"
        raise RuntimeError(f"Document indexing failed for {document.get('original_filename')}: {message}")


def wait_for_document_ready(
    client: httpx.Client,
    api_url: str,
    upload_result: dict[str, Any],
    poll_interval: float,
    timeout: float,
) -> dict[str, Any]:
    document_id = str(upload_result["document_id"])
    parse_task_id = str(upload_result.get("task_id") or "")
    deadline = time.monotonic() + timeout
    last_status = ""

    while time.monotonic() < deadline:
        document = get_document(client, api_url, document_id)
        assert_document_not_failed(document)
        task = get_task(client, api_url, parse_task_id) if parse_task_id else None
        status = (
            f"parse_status={document.get('parse_status')} "
            f"index_status={document.get('index_status')} "
            f"chunk_count={document.get('chunk_count')} "
            f"parse_task={task.get('status') if task else 'n/a'}"
        )
        if status != last_status:
            print(f"Waiting {document.get('original_filename')}: {status}")
            last_status = status
        if is_document_ready(document):
            return document
        time.sleep(poll_interval)

    document = get_document(client, api_url, document_id)
    raise TimeoutError(
        "Timed out waiting for document indexing: "
        f"{document.get('original_filename')} "
        f"parse_status={document.get('parse_status')} "
        f"index_status={document.get('index_status')}"
    )


def prepare_project(args: argparse.Namespace) -> str:
    api_url = normalize_api_url(args.api_url)
    papers_dir = args.papers_dir.expanduser().resolve(strict=False)
    documents_map_path = args.documents_map.expanduser().resolve(strict=False)

    print(f"Backend API: {api_url}")
    print(f"Papers dir: {papers_dir}")
    pdfs = find_pdfs(papers_dir)
    print(f"PDF count: {len(pdfs)}")

    with httpx.Client(timeout=args.request_timeout, trust_env=False) as client:
        project_id = create_project(client, api_url, args.project_name)
        print(f"Created project: {project_id}")

        upload_results: list[dict[str, Any]] = []
        documents_map: dict[str, dict[str, str]] = {}
        for index, pdf_path in enumerate(pdfs, start=1):
            paper_id = f"paper{index:03d}"
            print(f"Uploading {paper_id}: {pdf_path.name}")
            upload_result = upload_pdf(client, api_url, project_id, pdf_path)
            upload_results.append(upload_result)
            documents_map[paper_id] = {
                "document_id": str(upload_result["document_id"]),
                "file_name": pdf_path.name,
            }
            print(
                "Uploaded "
                f"paper_id={paper_id} "
                f"document_id={upload_result['document_id']} "
                f"task_id={upload_result.get('task_id')}"
            )

        ready_documents = []
        for upload_result in upload_results:
            ready_documents.append(
                wait_for_document_ready(
                    client=client,
                    api_url=api_url,
                    upload_result=upload_result,
                    poll_interval=args.poll_interval,
                    timeout=args.timeout,
                )
            )

    print("All documents are parsed, chunked, embedded, and indexed.")
    for document in ready_documents:
        print(
            f"- {document.get('original_filename')}: "
            f"chunks={document.get('chunk_count')} "
            f"document_id={document.get('id')}"
        )
    write_documents_map(documents_map_path, project_id, documents_map)
    print(f"PROJECT_ID={project_id}")
    print(f"Documents map: {documents_map_path}")
    print()
    print("Next command:")
    print(
        "python eval/run_rag_eval.py "
        f"--project-id {project_id} "
        f"--api-url {api_url} "
        f"--documents-map {documents_map_path}"
    )
    return project_id


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare a backend-only project for RAG evaluation.")
    parser.add_argument("--api-url", default=DEFAULT_API_URL)
    parser.add_argument("--papers-dir", type=Path, default=DEFAULT_PAPERS_DIR)
    parser.add_argument("--documents-map", type=Path, default=DEFAULT_DOCUMENTS_MAP)
    parser.add_argument("--project-name", default=DEFAULT_PROJECT_NAME)
    parser.add_argument("--poll-interval", type=float, default=3.0)
    parser.add_argument("--timeout", type=float, default=1800.0)
    parser.add_argument("--request-timeout", type=float, default=120.0)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        prepare_project(args)
    except Exception as exc:
        print(f"prepare_eval_project failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
