"""skills/stella_knowledge/skill.py - Stella Knowledge & Document Processing Skill."""
from __future__ import annotations
import json, time, uuid
from pathlib import Path
from typing import Any
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "memory" / "stella_knowledge"
DOCS_FILE = DATA_DIR / "documents.json"
PROJECTS_FILE = DATA_DIR / "projects.json"
KNOWLEDGE_FILE = DATA_DIR / "knowledge_graph.json"
FEATURE_METADATA = {"name": "stella_knowledge", "description": "Document and knowledge processing: agent management, project management, workflow automation, company-wide search, memory/knowledge graph for agents, agent chat and collaboration, observability.", "parameters": {"type": "OBJECT", "properties": {"operation": {"type": "STRING", "description": "add_document, list_documents, search_documents, add_project, list_projects, add_knowledge, search_knowledge, agent_chat, sources.", "default": "sources"}, "document_id": {"type": "STRING", "description": "Document ID for document operations."}, "title": {"type": "STRING", "description": "Document title."}, "content": {"type": "STRING", "description": "Document content."}, "project_id": {"type": "STRING", "description": "Project ID for project operations."}, "project_name": {"type": "STRING", "description": "Project name."}, "entity": {"type": "STRING", "description": "Knowledge graph entity name."}, "relation": {"type": "STRING", "description": "Knowledge graph relationship type."}, "target": {"type": "STRING", "description": "Knowledge graph target entity."}, "query": {"type": "STRING", "description": "Search query."}, "message": {"type": "STRING", "description": "Chat message for agent collaboration."}}, "required": []}, "version": "1.0.0", "active": True, "source": "paperclip", "optional_dependencies": [], "tags": ["knowledge", "document", "paperclip", "workflow", "observability"]}
def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
def _load(path: Path, default: Any) -> Any:
    _ensure_data_dir()
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default
def _save(path: Path, data: Any) -> None:
    _ensure_data_dir()
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
def _op_add_document(title: str, content: str) -> dict:
    docs = _load(DOCS_FILE, [])
    doc_id = str(uuid.uuid4())
    doc = {"document_id": doc_id, "title": title, "content": content, "created_at": time.time(), "updated_at": time.time()}
    docs.append(doc)
    _save(DOCS_FILE, docs)
    return {"ok": True, "document_id": doc_id, "document": doc}
def _op_list_documents() -> dict:
    docs = _load(DOCS_FILE, [])
    docs.sort(key=lambda d: d.get("updated_at", 0), reverse=True)
    return {"ok": True, "documents": docs, "count": len(docs)}
def _op_search_documents(query: str) -> dict:
    docs = _load(DOCS_FILE, [])
    if not query:
        return _op_list_documents()
    q = query.lower()
    results = [d for d in docs if q in d.get("title", "").lower() or q in d.get("content", "").lower()]
    results.sort(key=lambda d: d.get("updated_at", 0), reverse=True)
    return {"ok": True, "query": query, "documents": results, "count": len(results)}
def _op_add_project(project_name: str) -> dict:
    projects = _load(PROJECTS_FILE, [])
    project_id = str(uuid.uuid4())
    project = {"project_id": project_id, "name": project_name, "created_at": time.time(), "updated_at": time.time(), "documents": []}
    projects.append(project)
    _save(PROJECTS_FILE, projects)
    return {"ok": True, "project_id": project_id, "project": project}
def _op_list_projects() -> dict:
    projects = _load(PROJECTS_FILE, [])
    projects.sort(key=lambda p: p.get("updated_at", 0), reverse=True)
    return {"ok": True, "projects": projects, "count": len(projects)}
def _op_add_knowledge(entity: str, relation: str, target: str) -> dict:
    kg = _load(KNOWLEDGE_FILE, [])
    kg_id = str(uuid.uuid4())
    entry = {"knowledge_id": kg_id, "entity": entity, "relation": relation, "target": target, "created_at": time.time()}
    kg.append(entry)
    _save(KNOWLEDGE_FILE, kg)
    return {"ok": True, "knowledge_id": kg_id, "entry": entry}
def _op_search_knowledge(query: str) -> dict:
    kg = _load(KNOWLEDGE_FILE, [])
    if not query:
        return {"ok": True, "knowledge": kg, "count": len(kg)}
    q = query.lower()
    results = [e for e in kg if q in e.get("entity", "").lower() or q in e.get("target", "").lower() or q in e.get("relation", "").lower()]
    return {"ok": True, "query": query, "knowledge": results, "count": len(results)}
def _op_agent_chat(message: str) -> dict:
    docs = _load(DOCS_FILE, [])
    projects = _load(PROJECTS_FILE, [])
    kg = _load(KNOWLEDGE_FILE, [])
    response = "Stella Knowledge Agent received: " + message
    related_docs = [d["title"] for d in docs if message.lower() in d.get("title", "").lower()][:3]
    if related_docs:
        response += "\nRelated documents: " + ", ".join(related_docs)
    related_kg = [e for e in kg if message.lower() in e.get("entity", "").lower() or message.lower() in e.get("target", "").lower()][:3]
    if related_kg:
        response += "\nKnowledge connections: " + ", ".join(e["entity"] + " -> " + e["target"] for e in related_kg)
    return {"ok": True, "message": message, "response": response, "related_documents": related_docs, "knowledge_connections": related_kg}
def _op_sources() -> dict:
    return {"ok": True, "source": "paperclip", "skill": "stella_knowledge", "description": "Document and knowledge processing: agent management, project management, workflow automation, company-wide search, memory/knowledge graph for agents, agent chat and collaboration, observability.", "operations": ["add_document", "list_documents", "search_documents", "add_project", "list_projects", "add_knowledge", "search_knowledge", "agent_chat", "sources"], "cultural_origins": ["paperclip"], "api_key_required": False}
_OPERATIONS = {"add_document": _op_add_document, "list_documents": _op_list_documents, "search_documents": _op_search_documents, "add_project": _op_add_project, "list_projects": _op_list_projects, "add_knowledge": _op_add_knowledge, "search_knowledge": _op_search_knowledge, "agent_chat": _op_agent_chat, "sources": _op_sources}
_OPERATION_TITLES = {"add_document": "Add Document", "list_documents": "List Documents", "search_documents": "Search Documents", "add_project": "Add Project", "list_projects": "List Projects", "add_knowledge": "Add Knowledge", "search_knowledge": "Search Knowledge", "agent_chat": "Agent Chat", "sources": "Knowledge Sources"}
def execute(**kwargs) -> dict:
    operation = (kwargs.get("operation") or "sources").strip().lower()
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {"title": "Stella Knowledge", "summary": "Unknown operation '" + operation + "'.", "ok": False, "operation": operation}
    try:
        if operation == "add_document":
            record = handler(kwargs.get("title", ""), kwargs.get("content", ""))
        elif operation == "list_documents":
            record = handler()
        elif operation == "search_documents":
            record = handler(kwargs.get("query", ""))
        elif operation == "add_project":
            record = handler(kwargs.get("project_name", ""))
        elif operation == "list_projects":
            record = handler()
        elif operation == "add_knowledge":
            record = handler(kwargs.get("entity", ""), kwargs.get("relation", ""), kwargs.get("target", ""))
        elif operation == "search_knowledge":
            record = handler(kwargs.get("query", ""))
        elif operation == "agent_chat":
            record = handler(kwargs.get("message", ""))
        else:
            record = handler()
    except TypeError as exc:
        return {"title": "Stella Knowledge", "summary": "Bad arguments for '" + operation + "': " + str(exc), "ok": False, "operation": operation}
    except Exception as exc:
        return {"title": "Stella Knowledge", "summary": type(exc).__name__ + ": " + str(exc), "ok": False, "operation": operation}
    return {"title": _OPERATION_TITLES.get(operation, "Stella Knowledge"), "summary": str(record.get("error", record))[:200] if not record.get("ok") else str(record)[:200], "ok": bool(record.get("ok")), "operation": operation, "record": record}
if __name__ == "__main__":
    import pprint
    pprint.pprint(execute(operation="sources"))