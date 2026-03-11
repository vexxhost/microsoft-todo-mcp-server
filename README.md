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
| `list_tasks` | List tasks in a list (summaries, optional status filter) |
| `get_task` | Get full task details including body content |
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
