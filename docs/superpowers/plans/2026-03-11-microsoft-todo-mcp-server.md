# Microsoft To Do MCP Server Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and ship a Microsoft To Do MCP server in Python, launchable with `uvx`, using the Microsoft Graph SDK with zero-config interactive browser auth.

**Architecture:** Single-file FastMCP server (`server.py`) following the exact pattern of `entra-pim-mcp-server`. Auth via `azure-identity` `InteractiveBrowserCredential` with well-known Microsoft client ID. All 13 tools defined as async functions returning Pydantic models. Published to PyPI via `hatchling`.

**Tech Stack:** Python 3.11+, FastMCP (`mcp[cli]`), `msgraph-sdk`, `azure-identity`, `platformdirs`, `hatchling`, `ruff`

**Reference:** `/home/mnaser/src/github.com/vexxhost/entra-pim-mcp-server/` — follow its patterns exactly.

---

## Chunk 1: Project Scaffolding + Core Server

### Task 1: Create project boilerplate files

**Files:**
- Create: `pyproject.toml`
- Create: `src/microsoft_todo_mcp_server/__init__.py`
- Create: `.gitignore`
- Create: `LICENSE`
- Create: `.github/copilot-instructions.md`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "microsoft-todo-mcp-server"
version = "0.1.0"
description = "MCP server for Microsoft To Do — manage task lists, tasks, and checklist items via Graph API"
readme = "README.md"
license = "Apache-2.0"
requires-python = ">=3.11"
dependencies = [
    "mcp[cli]",
    "msgraph-sdk",
    "azure-identity",
    "platformdirs",
]

[project.scripts]
microsoft-todo-mcp-server = "microsoft_todo_mcp_server.server:main"

[dependency-groups]
dev = [
    "ruff>=0.15.5",
]

[tool.pyright]
reportMissingTypeStubs = false

[tool.ruff]
line-length = 120

[tool.ruff.lint]
select = ["E", "F", "W", "I"]
ignore = ["E501"]
```

- [ ] **Step 2: Create `src/microsoft_todo_mcp_server/__init__.py`**

Empty file.

- [ ] **Step 3: Create `.gitignore`**

Copy from reference project at `/home/mnaser/src/github.com/vexxhost/entra-pim-mcp-server/.gitignore`. Standard Python `.gitignore` with `.venv/`, `__pycache__/`, `*.egg-info/`, `.ruff_cache/`, `uv.lock` (keep it tracked), etc.

- [ ] **Step 4: Create `LICENSE`**

Apache-2.0 license. Copy from reference project at `/home/mnaser/src/github.com/vexxhost/entra-pim-mcp-server/LICENSE`.

- [ ] **Step 5: Create `.github/copilot-instructions.md`**

```markdown
## Git

- All commits must include a `Signed-off-by` trailer (`git commit -s`).

## Python

- Always use `uv` for Python operations (dependencies, virtual environments, running scripts).
```

- [ ] **Step 6: Install dependencies**

Run: `cd /home/mnaser/src/github.com/vexxhost/microsoft-todo-mcp-server && uv sync`
Expected: Dependencies installed, `uv.lock` generated, `.venv/` created.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -s -m "chore: initial project scaffolding

- pyproject.toml with hatchling build, mcp[cli]/msgraph-sdk/azure-identity deps
- Package structure under src/microsoft_todo_mcp_server/
- Apache-2.0 license, .gitignore, copilot-instructions"
```

---

### Task 2: Implement auth layer, Pydantic models, and main()

**Files:**
- Create: `src/microsoft_todo_mcp_server/server.py`

- [ ] **Step 1: Write the server file with auth, models, helper, and main()**

Create `src/microsoft_todo_mcp_server/server.py` with this content:

```python
"""Microsoft To Do MCP Server — manage task lists, tasks, and checklist items via Graph API."""

import asyncio
import os
import sys
from pathlib import Path

from azure.identity import (
    AuthenticationRecord,
    InteractiveBrowserCredential,
    TokenCachePersistenceOptions,
)
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from msgraph.generated.models.body_type import BodyType
from msgraph.generated.models.date_time_time_zone import DateTimeTimeZone
from msgraph.generated.models.importance import Importance
from msgraph.generated.models.item_body import ItemBody
from msgraph.generated.models.task_status import TaskStatus
from msgraph.generated.models.todo_task import TodoTask
from msgraph.generated.models.todo_task_list import TodoTaskList
from msgraph.graph_service_client import GraphServiceClient
from platformdirs import user_config_dir
from pydantic import BaseModel

# Well-known Microsoft Graph Command Line Tools client ID (first-party, multi-tenant)
GRAPH_CLIENT_ID = "14d82eec-204b-4c2f-b7e8-296a70dab67e"

GRAPH_SCOPES = [
    "Tasks.ReadWrite",
    "User.Read",
]

CONFIG_DIR = Path(user_config_dir("microsoft-todo-mcp-server"))
AUTH_RECORD_PATH = CONFIG_DIR / "auth-record.json"


def _load_auth_record() -> AuthenticationRecord | None:
    try:
        data = AUTH_RECORD_PATH.read_text()
        return AuthenticationRecord.deserialize(data)
    except (FileNotFoundError, ValueError):
        return None


def _save_auth_record(record: AuthenticationRecord) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    AUTH_RECORD_PATH.write_text(record.serialize())


_client: GraphServiceClient | None = None


async def get_client() -> GraphServiceClient:
    global _client
    if _client is not None:
        return _client

    tenant_id = os.environ.get("AZURE_TENANT_ID", "common")

    auth_record = _load_auth_record()

    credential = InteractiveBrowserCredential(
        tenant_id=tenant_id,
        client_id=GRAPH_CLIENT_ID,
        redirect_uri="http://localhost:8400",
        authentication_record=auth_record,
        cache_persistence_options=TokenCachePersistenceOptions(
            name="microsoft-todo-mcp-server",
            allow_unencrypted_storage=True,
        ),
    )

    if auth_record is None:
        new_record = await asyncio.to_thread(credential.authenticate, scopes=GRAPH_SCOPES)
        _save_auth_record(new_record)

    _client = GraphServiceClient(credentials=credential, scopes=GRAPH_SCOPES)
    return _client


# --- Pydantic result models ---


class TaskListResult(BaseModel):
    id: str
    display_name: str


class ListTaskListsResult(BaseModel):
    task_lists: list[TaskListResult]


class TaskResult(BaseModel):
    id: str
    title: str
    status: str
    importance: str
    body_content: str | None
    body_content_type: str | None
    due_date: str | None
    created_at: str
    completed_at: str | None


class ListTasksResult(BaseModel):
    tasks: list[TaskResult]


class ChecklistItemResult(BaseModel):
    id: str
    display_name: str
    is_checked: bool


class ListChecklistItemsResult(BaseModel):
    checklist_items: list[ChecklistItemResult]


class DeleteResult(BaseModel):
    message: str


# --- Helpers ---


def _task_to_result(task: TodoTask) -> TaskResult:
    body_content = None
    body_content_type = None
    if task.body:
        body_content = task.body.content
        body_content_type = task.body.content_type.value if task.body.content_type else None

    due_date = None
    if task.due_date_time:
        due_date = task.due_date_time.date_time

    completed_at = None
    if task.completed_date_time:
        completed_at = task.completed_date_time.date_time

    return TaskResult(
        id=task.id or "",
        title=task.title or "",
        status=task.status.value if task.status else "notStarted",
        importance=task.importance.value if task.importance else "normal",
        body_content=body_content,
        body_content_type=body_content_type,
        due_date=due_date,
        created_at=task.created_date_time.isoformat() if task.created_date_time else "",
        completed_at=completed_at,
    )


def _checklist_to_result(item: "GraphChecklistItem") -> ChecklistItemResult:
    return ChecklistItemResult(
        id=item.id or "",
        display_name=item.display_name or "",
        is_checked=item.is_checked if item.is_checked is not None else False,
    )


mcp = FastMCP("microsoft-todo-mcp-server")


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
```

Note: `GraphChecklistItem` is used as a forward reference string because the import name `ChecklistItem` from `msgraph.generated.models.checklist_item` conflicts with our Pydantic model. Add this import at the top:

```python
from msgraph.generated.models.checklist_item import ChecklistItem as GraphChecklistItem
```

And remove the forward reference quotes from `_checklist_to_result`.

- [ ] **Step 2: Verify lint passes**

Run: `cd /home/mnaser/src/github.com/vexxhost/microsoft-todo-mcp-server && uv run ruff check src/`
Expected: No errors (or only import-order auto-fixable).

If ruff reports import order issues, run: `uv run ruff check --fix src/`

- [ ] **Step 3: Verify the package is importable**

Run: `cd /home/mnaser/src/github.com/vexxhost/microsoft-todo-mcp-server && uv run python -c "from microsoft_todo_mcp_server.server import mcp; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -s -m "feat: add auth layer, pydantic models, and server skeleton

- InteractiveBrowserCredential with well-known Graph CLI client ID
- Token cache persistence via platformdirs
- Optional AZURE_TENANT_ID override (default: common)
- Pydantic result models for task lists, tasks, checklist items
- Helper functions for Graph model -> Pydantic conversion
- FastMCP server with stdio transport"
```

---

### Task 3: Implement task list tools (4 tools)

**Files:**
- Modify: `src/microsoft_todo_mcp_server/server.py`

- [ ] **Step 1: Add `list_task_lists` tool**

Add before the `main()` function:

```python
@mcp.tool(
    title="List task lists",
    structured_output=True,
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ),
)
async def list_task_lists() -> ListTaskListsResult:
    """List all Microsoft To Do task lists."""
    client = await get_client()
    result = await client.me.todo.lists.get()
    task_lists = []
    if result and result.value:
        for tl in result.value:
            task_lists.append(TaskListResult(
                id=tl.id or "",
                display_name=tl.display_name or "",
            ))
    return ListTaskListsResult(task_lists=task_lists)
```

- [ ] **Step 2: Add `create_task_list` tool**

```python
@mcp.tool(
    title="Create task list",
    structured_output=True,
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=False,
    ),
)
async def create_task_list(display_name: str) -> TaskListResult:
    """Create a new Microsoft To Do task list."""
    client = await get_client()
    body = TodoTaskList(display_name=display_name)
    result = await client.me.todo.lists.post(body)
    if not result:
        raise RuntimeError("Failed to create task list.")
    return TaskListResult(
        id=result.id or "",
        display_name=result.display_name or "",
    )
```

- [ ] **Step 3: Add `update_task_list` tool**

```python
@mcp.tool(
    title="Update task list",
    structured_output=True,
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ),
)
async def update_task_list(list_id: str, display_name: str) -> TaskListResult:
    """Update the display name of a Microsoft To Do task list."""
    client = await get_client()
    body = TodoTaskList(display_name=display_name)
    result = await client.me.todo.lists.by_todo_task_list_id(list_id).patch(body)
    if not result:
        raise RuntimeError("Failed to update task list.")
    return TaskListResult(
        id=result.id or "",
        display_name=result.display_name or "",
    )
```

- [ ] **Step 4: Add `delete_task_list` tool**

```python
@mcp.tool(
    title="Delete task list",
    structured_output=True,
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=True,
        idempotentHint=False,
        openWorldHint=False,
    ),
)
async def delete_task_list(list_id: str) -> DeleteResult:
    """Delete a Microsoft To Do task list and all its tasks."""
    client = await get_client()
    await client.me.todo.lists.by_todo_task_list_id(list_id).delete()
    return DeleteResult(message=f"Task list '{list_id}' deleted successfully.")
```

- [ ] **Step 5: Lint check**

Run: `uv run ruff check src/`
Expected: No errors.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -s -m "feat: add task list CRUD tools

- list_task_lists: list all To Do task lists
- create_task_list: create a new task list
- update_task_list: rename a task list
- delete_task_list: delete a task list"
```

---

### Task 4: Implement task tools (5 tools)

**Files:**
- Modify: `src/microsoft_todo_mcp_server/server.py`

- [ ] **Step 1: Add `list_tasks` tool**

Add after the task list tools, before `main()`:

```python
@mcp.tool(
    title="List tasks",
    structured_output=True,
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ),
)
async def list_tasks(
    list_id: str,
    status: str | None = None,
) -> ListTasksResult:
    """List tasks in a Microsoft To Do task list. Optionally filter by status: notStarted, inProgress, completed, waitingOnOthers, deferred."""
    client = await get_client()
    result = await client.me.todo.lists.by_todo_task_list_id(list_id).tasks.get()
    tasks = []
    if result and result.value:
        for task in result.value:
            task_result = _task_to_result(task)
            if status and task_result.status != status:
                continue
            tasks.append(task_result)
    return ListTasksResult(tasks=tasks)
```

- [ ] **Step 2: Add `create_task` tool**

```python
@mcp.tool(
    title="Create task",
    structured_output=True,
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=False,
    ),
)
async def create_task(
    list_id: str,
    title: str,
    body: str | None = None,
    due_date: str | None = None,
    importance: str | None = None,
) -> TaskResult:
    """Create a new task in a Microsoft To Do task list. due_date should be YYYY-MM-DD format. importance can be: low, normal, high."""
    client = await get_client()
    task = TodoTask(title=title)

    if body is not None:
        task.body = ItemBody(content=body, content_type=BodyType.Text)

    if due_date is not None:
        task.due_date_time = DateTimeTimeZone(date_time=f"{due_date}T00:00:00.0000000", time_zone="UTC")

    if importance is not None:
        task.importance = Importance(importance)

    result = await client.me.todo.lists.by_todo_task_list_id(list_id).tasks.post(task)
    if not result:
        raise RuntimeError("Failed to create task.")
    return _task_to_result(result)
```

- [ ] **Step 3: Add `update_task` tool**

```python
@mcp.tool(
    title="Update task",
    structured_output=True,
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ),
)
async def update_task(
    list_id: str,
    task_id: str,
    title: str | None = None,
    body: str | None = None,
    due_date: str | None = None,
    importance: str | None = None,
    status: str | None = None,
) -> TaskResult:
    """Update a task in a Microsoft To Do task list. Only provided fields are updated."""
    client = await get_client()
    task = TodoTask()

    if title is not None:
        task.title = title

    if body is not None:
        task.body = ItemBody(content=body, content_type=BodyType.Text)

    if due_date is not None:
        task.due_date_time = DateTimeTimeZone(date_time=f"{due_date}T00:00:00.0000000", time_zone="UTC")

    if importance is not None:
        task.importance = Importance(importance)

    if status is not None:
        task.status = TaskStatus(status)

    result = await client.me.todo.lists.by_todo_task_list_id(list_id).tasks.by_todo_task_id(task_id).patch(task)
    if not result:
        raise RuntimeError("Failed to update task.")
    return _task_to_result(result)
```

- [ ] **Step 4: Add `complete_task` tool**

```python
@mcp.tool(
    title="Complete task",
    structured_output=True,
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ),
)
async def complete_task(list_id: str, task_id: str) -> TaskResult:
    """Mark a Microsoft To Do task as completed."""
    client = await get_client()
    task = TodoTask(status=TaskStatus.Completed)
    result = await client.me.todo.lists.by_todo_task_list_id(list_id).tasks.by_todo_task_id(task_id).patch(task)
    if not result:
        raise RuntimeError("Failed to complete task.")
    return _task_to_result(result)
```

- [ ] **Step 5: Add `delete_task` tool**

```python
@mcp.tool(
    title="Delete task",
    structured_output=True,
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=True,
        idempotentHint=False,
        openWorldHint=False,
    ),
)
async def delete_task(list_id: str, task_id: str) -> DeleteResult:
    """Delete a task from a Microsoft To Do task list."""
    client = await get_client()
    await client.me.todo.lists.by_todo_task_list_id(list_id).tasks.by_todo_task_id(task_id).delete()
    return DeleteResult(message=f"Task '{task_id}' deleted successfully.")
```

- [ ] **Step 6: Lint check**

Run: `uv run ruff check src/`
Expected: No errors.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -s -m "feat: add task CRUD tools

- list_tasks: list tasks with optional status filter
- create_task: create task with title, body, due date, importance
- update_task: update any task field
- complete_task: mark task as completed
- delete_task: delete a task"
```

---

## Chunk 2: Checklist Tools + README + Verification

### Task 5: Implement checklist item tools (4 tools)

**Files:**
- Modify: `src/microsoft_todo_mcp_server/server.py`

- [ ] **Step 1: Add `list_checklist_items` tool**

Add after the task tools, before `main()`:

```python
@mcp.tool(
    title="List checklist items",
    structured_output=True,
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ),
)
async def list_checklist_items(list_id: str, task_id: str) -> ListChecklistItemsResult:
    """List checklist items (subtasks) of a Microsoft To Do task."""
    client = await get_client()
    result = await client.me.todo.lists.by_todo_task_list_id(list_id).tasks.by_todo_task_id(task_id).checklist_items.get()
    items = []
    if result and result.value:
        for item in result.value:
            items.append(_checklist_to_result(item))
    return ListChecklistItemsResult(checklist_items=items)
```

- [ ] **Step 2: Add `create_checklist_item` tool**

```python
@mcp.tool(
    title="Create checklist item",
    structured_output=True,
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=False,
    ),
)
async def create_checklist_item(list_id: str, task_id: str, display_name: str) -> ChecklistItemResult:
    """Add a checklist item (subtask) to a Microsoft To Do task."""
    client = await get_client()
    body = GraphChecklistItem(display_name=display_name)
    result = await client.me.todo.lists.by_todo_task_list_id(list_id).tasks.by_todo_task_id(task_id).checklist_items.post(body)
    if not result:
        raise RuntimeError("Failed to create checklist item.")
    return _checklist_to_result(result)
```

- [ ] **Step 3: Add `update_checklist_item` tool**

```python
@mcp.tool(
    title="Update checklist item",
    structured_output=True,
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ),
)
async def update_checklist_item(
    list_id: str,
    task_id: str,
    checklist_item_id: str,
    display_name: str | None = None,
    is_checked: bool | None = None,
) -> ChecklistItemResult:
    """Update a checklist item (subtask) of a Microsoft To Do task. Use is_checked to check/uncheck."""
    client = await get_client()
    body = GraphChecklistItem()
    if display_name is not None:
        body.display_name = display_name
    if is_checked is not None:
        body.is_checked = is_checked
    result = await client.me.todo.lists.by_todo_task_list_id(list_id).tasks.by_todo_task_id(task_id).checklist_items.by_checklist_item_id(checklist_item_id).patch(body)
    if not result:
        raise RuntimeError("Failed to update checklist item.")
    return _checklist_to_result(result)
```

- [ ] **Step 4: Add `delete_checklist_item` tool**

```python
@mcp.tool(
    title="Delete checklist item",
    structured_output=True,
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=True,
        idempotentHint=False,
        openWorldHint=False,
    ),
)
async def delete_checklist_item(list_id: str, task_id: str, checklist_item_id: str) -> DeleteResult:
    """Delete a checklist item (subtask) from a Microsoft To Do task."""
    client = await get_client()
    await client.me.todo.lists.by_todo_task_list_id(list_id).tasks.by_todo_task_id(task_id).checklist_items.by_checklist_item_id(checklist_item_id).delete()
    return DeleteResult(message=f"Checklist item '{checklist_item_id}' deleted successfully.")
```

- [ ] **Step 5: Lint check**

Run: `uv run ruff check src/`
Expected: No errors.

- [ ] **Step 6: Import verification**

Run: `uv run python -c "from microsoft_todo_mcp_server.server import mcp; print(f'Tools: {len(mcp._tool_manager._tools)}')"`
Expected: `Tools: 13`

Note: If the `_tool_manager._tools` attribute path doesn't work, try: `uv run python -c "from microsoft_todo_mcp_server.server import mcp; print('OK')"` to at least verify imports.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -s -m "feat: add checklist item CRUD tools

- list_checklist_items: list subtasks of a task
- create_checklist_item: add a subtask
- update_checklist_item: update name or check/uncheck
- delete_checklist_item: delete a subtask"
```

---

### Task 6: Write README.md

**Files:**
- Create: `README.md`

- [ ] **Step 1: Create README.md**

```markdown
# microsoft-todo-mcp-server

MCP server for Microsoft To Do — manage task lists, tasks, and checklist items via the Microsoft Graph API.

## Features

- **13 MCP tools** for full CRUD on task lists, tasks, and checklist items
- **Zero-config authentication** — uses a well-known Microsoft client ID, no app registration needed
- **Interactive browser login** — opens your browser on first run, then caches credentials
- **Launch with uvx** — no installation required

## Quick Start

### Claude Desktop / Copilot / any MCP client

Add to your MCP client configuration:

```json
{
  "mcpServers": {
    "microsoft-todo": {
      "command": "uvx",
      "args": ["microsoft-todo-mcp-server"]
    }
  }
}
```

On first launch, your browser will open for Microsoft sign-in. After that, credentials are cached and sign-in is automatic.

### Optional: Specify a tenant

If your organization requires a specific Azure AD tenant (e.g., due to conditional access policies), set the `AZURE_TENANT_ID` environment variable:

```json
{
  "mcpServers": {
    "microsoft-todo": {
      "command": "uvx",
      "args": ["microsoft-todo-mcp-server"],
      "env": {
        "AZURE_TENANT_ID": "your-tenant-id"
      }
    }
  }
}
```

By default, the server uses the `common` tenant which works with any Microsoft account (personal or work/school).

## Available Tools

### Task Lists

| Tool | Description |
|------|-------------|
| `list_task_lists` | List all task lists |
| `create_task_list` | Create a new task list |
| `update_task_list` | Rename a task list |
| `delete_task_list` | Delete a task list |

### Tasks

| Tool | Description |
|------|-------------|
| `list_tasks` | List tasks in a list (optional status filter) |
| `create_task` | Create a task with title, body, due date, importance |
| `update_task` | Update any task fields |
| `complete_task` | Mark a task as completed |
| `delete_task` | Delete a task |

### Checklist Items (Subtasks)

| Tool | Description |
|------|-------------|
| `list_checklist_items` | List subtasks of a task |
| `create_checklist_item` | Add a subtask |
| `update_checklist_item` | Update or check/uncheck a subtask |
| `delete_checklist_item` | Delete a subtask |

## Authentication

This server uses Microsoft's well-known "Graph Command Line Tools" client ID for authentication. No Azure AD app registration is required.

On first run:
1. Your browser opens to Microsoft's login page
2. Sign in with your Microsoft account (personal or work/school)
3. Consent to the requested permissions (Tasks.ReadWrite, User.Read)
4. Credentials are cached locally for future use

Token cache is stored in your platform's config directory (e.g., `~/.config/microsoft-todo-mcp-server/` on Linux).

## Development

```bash
# Clone the repository
git clone https://github.com/vexxhost/microsoft-todo-mcp-server.git
cd microsoft-todo-mcp-server

# Install dependencies
uv sync

# Run the server locally
uv run microsoft-todo-mcp-server

# Lint
uv run ruff check src/
```

## License

Apache-2.0
```

- [ ] **Step 2: Commit**

```bash
git add -A
git commit -s -m "docs: add README with usage, tools, and auth documentation"
```

---

### Task 7: Final lint, build, and verification

**Files:**
- No new files

- [ ] **Step 1: Run full lint**

Run: `cd /home/mnaser/src/github.com/vexxhost/microsoft-todo-mcp-server && uv run ruff check src/`
Expected: No errors.

- [ ] **Step 2: Verify package builds**

Run: `cd /home/mnaser/src/github.com/vexxhost/microsoft-todo-mcp-server && uv build`
Expected: Builds a wheel and sdist in `dist/` without errors.

- [ ] **Step 3: Verify entry point works**

Run: `cd /home/mnaser/src/github.com/vexxhost/microsoft-todo-mcp-server && echo '{}' | timeout 3 uv run microsoft-todo-mcp-server 2>&1 || true`
Expected: Server starts (may exit with EOF on stdin since there's no MCP client, but should NOT crash with an import error or missing dependency).

- [ ] **Step 4: Clean up build artifacts**

Run: `rm -rf dist/`

- [ ] **Step 5: Final commit if any fixes were needed**

Only if previous steps required fixes:
```bash
git add -A
git commit -s -m "fix: address lint/build issues"
```
