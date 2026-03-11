# Changelog

## 0.1.0 (2026-03-11)


### Features

* add get_task tool, trim body from list_tasks ([28ff042](https://github.com/vexxhost/microsoft-todo-mcp-server/commit/28ff04276f1ee7be654b6e2a1cbb87d47c7eacff))
* add has_more pagination hint to list_tasks response ([84bdcbb](https://github.com/vexxhost/microsoft-todo-mcp-server/commit/84bdcbb81913bd57f76ca3ae839609fe441c0d53))
* expose OData query parameters on list_tasks ([7a7f467](https://github.com/vexxhost/microsoft-todo-mcp-server/commit/7a7f467b8ab44275157274a2b5fa2a6c075cabcb))
* implement full MCP server with 13 tools ([b96c4f6](https://github.com/vexxhost/microsoft-todo-mcp-server/commit/b96c4f63ba3e8cab24563c9d439d3ca659ce89f5))
* limit list_tasks to 25 results by default ([293d22c](https://github.com/vexxhost/microsoft-todo-mcp-server/commit/293d22c59ab99f3be75bd59ac2e39368b4ba6980))
* return count and next_link instead of has_more ([a826f24](https://github.com/vexxhost/microsoft-todo-mcp-server/commit/a826f243014022df77d703ce0405825d3b925f1f))


### Bug Fixes

* use list[str] for orderby parameter ([1f78825](https://github.com/vexxhost/microsoft-todo-mcp-server/commit/1f78825bb4fb308889d87f64ce116d8c21a2eaa9))
* use server-side OData filter for task status ([b673eff](https://github.com/vexxhost/microsoft-todo-mcp-server/commit/b673effc1cfe5c278079b2ae057f49116ac913d1))


### Documentation

* add README with usage, tools, and auth documentation ([71cce2b](https://github.com/vexxhost/microsoft-todo-mcp-server/commit/71cce2bd3e094566d269d372ed947f80bbecaa1d))
