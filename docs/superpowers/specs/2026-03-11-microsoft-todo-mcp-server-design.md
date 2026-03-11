# Microsoft To Do MCP Server — Design Spec

## Problem

Build an MCP server that exposes Microsoft To Do functionality via the Graph API, packaged as a Python CLI tool launchable with `uvx`. The server should use interactive browser authentication with a well-known Microsoft client ID so users don't need to register their own Azure AD application.

## Approach

Follow the same architecture as `entra-pim-mcp-server`: single-file FastMCP server, `azure-identity` for authentication, `msgraph-sdk` for API calls, published to PyPI via `hatchling`.

## Authentication

- **Client ID:** `14d82eec-204b-4c2f-b7e8-296a70dab67e` (Microsoft Graph Command Line Tools — first-party multi-tenant public client)
- **Credential:** `InteractiveBrowserCredential` from `azure-identity`
- **Token persistence:** `TokenCachePersistenceOptions` with named cache `microsoft-todo-mcp-server` and `allow_unencrypted_storage=True`
- **Auth record:** Serialized to `~/.config/microsoft-todo-mcp-server/auth-record.json` via `platformdirs`
- **Redirect URI:** `http://localhost:8400`
- **Tenant ID:** Default to `"common"` authority for multi-tenant support (works with any org or personal Microsoft account). Optionally override via `AZURE_TENANT_ID` env var for orgs with conditional access policies that block the common endpoint.
- **Scopes:** `Tasks.ReadWrite`, `User.Read`
- **Flow:** On first run, browser opens for interactive consent. Subsequent runs use cached tokens with silent refresh. `azure-identity` handles refresh tokens implicitly via its token cache.

## MCP Tools

### Task Lists

| Tool | Parameters | Returns | Annotations |
|------|-----------|---------|-------------|
| `list_task_lists` | (none) | List of task lists with id, name | readOnly, idempotent |
| `create_task_list` | `display_name: str` | Created task list | not readOnly, not destructive |
| `update_task_list` | `list_id: str, display_name: str` | Updated task list | not readOnly, not destructive |
| `delete_task_list` | `list_id: str` | Confirmation message | destructive |

### Tasks

| Tool | Parameters | Returns | Annotations |
|------|-----------|---------|-------------|
| `list_tasks` | `list_id: str, status: Optional[str]` | List of tasks with details | readOnly, idempotent |
| `create_task` | `list_id: str, title: str, body: Optional[str], due_date: Optional[str], importance: Optional[str]` | Created task | not readOnly |
| `update_task` | `list_id: str, task_id: str, title: Optional[str], body: Optional[str], due_date: Optional[str], importance: Optional[str], status: Optional[str]` | Updated task | not readOnly |
| `complete_task` | `list_id: str, task_id: str` | Updated task (status=completed) | not readOnly |
| `delete_task` | `list_id: str, task_id: str` | Confirmation message | destructive |

### Checklist Items (Subtasks)

| Tool | Parameters | Returns | Annotations |
|------|-----------|---------|-------------|
| `list_checklist_items` | `list_id: str, task_id: str` | List of checklist items | readOnly, idempotent |
| `create_checklist_item` | `list_id: str, task_id: str, display_name: str` | Created checklist item | not readOnly |
| `update_checklist_item` | `list_id: str, task_id: str, checklist_item_id: str, display_name: Optional[str], is_checked: Optional[bool]` | Updated checklist item | not readOnly |
| `delete_checklist_item` | `list_id: str, task_id: str, checklist_item_id: str` | Confirmation message | destructive |

All tools use `structured_output=True` and set all four `ToolAnnotations` fields: `readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`.

## Data Models (Pydantic)

```python
class TaskList(BaseModel):
    id: str
    display_name: str

class Task(BaseModel):
    id: str
    title: str
    status: str  # notStarted, inProgress, completed, waitingOnOthers, deferred
    importance: str  # low, normal, high
    body_content: str | None  # extracted from Graph API's itemBody.content
    body_content_type: str | None  # "text" or "html"
    due_date: str | None
    created_at: str
    completed_at: str | None

class ChecklistItem(BaseModel):
    id: str
    display_name: str
    is_checked: bool
```

## Project Structure

```
microsoft-todo-mcp-server/
├── src/
│   └── microsoft_todo_mcp_server/
│       ├── __init__.py
│       └── server.py          # All server logic
├── pyproject.toml
├── README.md
├── LICENSE                     # Apache-2.0
└── docs/
    └── superpowers/
        └── specs/
            └── 2026-03-11-microsoft-todo-mcp-server-design.md
```

## pyproject.toml

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

## Usage

### Launch with uvx

```bash
uvx microsoft-todo-mcp-server
```

### MCP Client Configuration

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

No environment variables required — the well-known client ID and `"common"` tenant are embedded. Optional override: `AZURE_TENANT_ID` for orgs requiring a specific tenant.

## Error Handling

- Token expiry: Handled automatically by `azure-identity` silent refresh
- Invalid list/task IDs: Surface Graph API error messages
- Network errors: Let exceptions propagate to MCP framework
- First-run auth: Browser opens automatically; if auth fails, raise RuntimeError with clear message

## Testing Approach

- Manual testing against a real Microsoft 365 account
- Verify all 13 tools work end-to-end
- Verify token persistence (restart server, confirm no re-auth needed)
