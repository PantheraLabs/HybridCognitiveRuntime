
---

## 2026-05-01 - Commercial-Ready Async Transport Upgrade

**Status:** PRODUCTION READY - High-Performance MCP Implementation

### Implementation
- **Non-Blocking I/O**: Implemented a dedicated background reader thread and `asyncio.Queue` to decouple stdin reading from the event loop.
- **Concurreny & Tracking**: Switched to a full task-tracking architecture. Every request spawns an independent `asyncio.Task`.
- **Cancellation Support**: Added support for `notifications/cancelled`. The server can now abort long-running engine operations if the client cancels the request.
- **Graceful Shutdown**: Added cleanup logic to cancel all pending tasks and close the thread pool properly on EOF or SIGINT.
- **Verification**: Verified with `scratch/test_commercial_mcp.py` demonstrating simultaneous request processing and task tracking.

### Files Updated
- `product/integrations/mcp_server.py` - Complete refactor of `MCPServerStdio` transport layer.
