"""Microsoft To Do MCP Server — manage task lists, tasks, and checklist items via Graph API."""

import asyncio
import os
from pathlib import Path

from azure.identity import (
    AuthenticationRecord,
    InteractiveBrowserCredential,
    TokenCachePersistenceOptions,
)
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from msgraph.generated.models.body_type import BodyType
from msgraph.generated.models.checklist_item import ChecklistItem as GraphChecklistItem
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


def _checklist_to_result(item: GraphChecklistItem) -> ChecklistItemResult:
    return ChecklistItemResult(
        id=item.id or "",
        display_name=item.display_name or "",
        is_checked=item.is_checked if item.is_checked is not None else False,
    )


# --- FastMCP server ---

mcp = FastMCP("microsoft-todo-mcp-server")


# --- Task List tools ---


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


# --- Task tools ---


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


# --- Checklist item tools ---


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


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
