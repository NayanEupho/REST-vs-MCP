import asyncio
import json
import time
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

app = FastAPI(title="MCP Server")

# In-memory session store for SSE connections
sessions: Dict[str, asyncio.Queue] = {}

class JsonRpcRequest(BaseModel):
    jsonrpc: str
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[int | str] = None

class JsonRpcResponse(BaseModel):
    jsonrpc: str = "2.0"
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[int | str] = None

@app.get("/sse")
async def sse_endpoint(request: Request):
    """
    Server-Sent Events endpoint for MCP transport.
    """
    async def event_generator():
        session_id = str(time.time()) # Simple session ID
        queue = asyncio.Queue()
        sessions[session_id] = queue
        
        # Send initial connection event if needed, or just keep open
        yield f"event: connection\ndata: {session_id}\n\n"
        
        try:
            while True:
                # 1. Check for queued messages (responses/notifications)
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=0.1)
                    yield f"data: {json.dumps(message)}\n\n"
                except asyncio.TimeoutError:
                    pass
                
                # 2. Simulate Stock Ticker Updates (Global Push)
                # Push to everyone every 1s approx
                if int(time.time() * 10) % 10 == 0: 
                     import random
                     price = 100.0 + random.uniform(-5.0, 5.0)
                     msg = {
                         "jsonrpc": "2.0", 
                         "method": "notifications/resources/updated", 
                         "params": {
                             "uri": "stock://ticker", 
                             "delta": {"price": round(price, 2), "timestamp": time.time()}
                         }
                     }
                     yield f"data: {json.dumps(msg)}\n\n"
                     await asyncio.sleep(0.1) # Avoid spamming
                     
                if await request.is_disconnected():
                    break
        finally:
            del sessions[session_id]

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.post("/message")
async def handle_message(request: JsonRpcRequest):
    """
    Handle incoming JSON-RPC messages from client.
    """
    response = await process_json_rpc(request)
    return response

async def run_mcp_task(session_id: str, complexity: int):
    queue = sessions.get(session_id)
    if not queue:
        return

    for i in range(10):
        await asyncio.sleep(0.1 * complexity)
        progress = (i + 1) * 10
        # Send Notification
        notification = {
            "jsonrpc": "2.0",
            "method": "notifications/progress",
            "params": {"progress": progress, "status": "running"}
        }
        await queue.put(notification)
        
    # Final completion
    completion = {
        "jsonrpc": "2.0",
        "method": "notifications/progress",
        "params": {"progress": 100, "status": "completed", "result": "Task Completed Successfully"}
    }
    await queue.put(completion)

async def process_json_rpc(request: JsonRpcRequest) -> JsonRpcResponse:
    if request.method == "initialize":
        return JsonRpcResponse(
            id=request.id,
            result={
                "protocolVersion": "0.1.0",
                "capabilities": {
                    "tools": {},
                    "resources": {}
                },
                "serverInfo": {
                    "name": "mcp-python-demo",
                    "version": "1.0.0"
                }
            }
        )
    
    elif request.method == "tools/list":
        return JsonRpcResponse(
            id=request.id,
            result={
                "tools": [
                    {
                        "name": "calculate",
                        "description": "Perform basic arithmetic operations",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "operation": {"type": "string", "enum": ["add", "subtract", "multiply", "divide"]},
                                "a": {"type": "number"},
                                "b": {"type": "number"}
                            },
                            "required": ["operation", "a", "b"]
                        }
                    },
                    {
                        "name": "generate_task",
                        "description": "Start a long-running task",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "complexity": {"type": "integer"},
                                "sessionId": {"type": "string"}
                            },
                            "required": ["complexity", "sessionId"]
                        }
                    },
                    {
                        "name": "workflow_step",
                        "description": "Execute a workflow step",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "step": {"type": "integer", "enum": [1, 2, 3]},
                                "input_data": {"type": "string"}
                            },
                            "required": ["step", "input_data"]
                        }
                    }
                ]
            }
        )
    
    elif request.method == "prompts/chat":
        # Stateful Chat
        params = request.params or {}
        session_id = params.get("sessionId")
        message = params.get("message")
        
        if not session_id:
             return JsonRpcResponse(id=request.id, error={"code": -32602, "message": "Missing sessionId"})

        # In a real implementation, we'd look up the session history
        # Here we simulate statefulness by NOT requiring history in the request
        # We assume the server "knows" the context.
        
        # Simulate processing time based on "accumulated" context
        # We'll just pretend context grows by 100 chars per turn
        turn_count = params.get("turnCount", 1)
        context_length = turn_count * 100 + len(message)
        delay = context_length * 0.0001
        await asyncio.sleep(delay)
        
        return JsonRpcResponse(
            id=request.id,
            result={
                "response": f"Echo: {message} (Stateful Context: {turn_count} turns)",
                "usage": context_length
            }
        )

    elif request.method == "tools/call":
        params = request.params or {}
        name = params.get("name")
        args = params.get("arguments", {})
        
        if name == "calculate":
            # Simulate computation
            await asyncio.sleep(0.01)
            
            op = args.get("operation")
            a = args.get("a", 0)
            b = args.get("b", 0)
            
            if op == "add":
                res = a + b
            elif op == "subtract":
                res = a - b
            elif op == "multiply":
                res = a * b
            elif op == "divide":
                res = a / b if b != 0 else "Error: Division by zero"
            else:
                res = "Error: Unknown operation"
                
            return JsonRpcResponse(
                id=request.id,
                result={
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps({"result": res, "operation": op})
                        }
                    ]
                }
            )
        elif name == "generate_task":
            # Long-running task with Push Notifications
            complexity = args.get("complexity", 1)
            session_id = args.get("sessionId") # We need session ID to push events
            
            if session_id and session_id in sessions:
                asyncio.create_task(run_mcp_task(session_id, complexity))
                return JsonRpcResponse(
                    id=request.id,
                    result={
                        "content": [{"type": "text", "text": "Task Started"}]
                    }
                )
            else:
                 return JsonRpcResponse(
                    id=request.id,
                    error={"code": -32602, "message": "Invalid or missing sessionId"}
                )


        elif name == "workflow_step":
            step = args.get("step")
            data = args.get("input_data")
            
            if step == 1:
                await asyncio.sleep(0.05)
                res = f"Processed({data})"
            elif step == 2:
                await asyncio.sleep(0.1)
                res = f"Analyzed({data})"
            elif step == 3:
                await asyncio.sleep(0.2)
                res = f"Summary({data})"
            else:
                return JsonRpcResponse(id=request.id, error={"code": -32602, "message": "Invalid step"})
                
            return JsonRpcResponse(
                id=request.id,
                result={
                    "content": [{"type": "text", "text": json.dumps({"output": res, "step": step})}]
                }
            )

        else:
             return JsonRpcResponse(
                id=request.id,
                error={"code": -32601, "message": "Method not found"}
            )

    elif request.method == "resources/list":
        return JsonRpcResponse(
            id=request.id,
            result={
                "resources": [
                    {"uri": "file:///logs/system.log", "name": "System Logs", "mimeType": "text/plain"},
                    {"uri": "stock://ticker", "name": "Stock Ticker (MCP)", "mimeType": "application/json"}
                ]
            }
        )
    elif request.method == "resources/read":
        params = request.params or {}
        uri = params.get("uri")
        if uri == "file:///logs/system.log":
             return JsonRpcResponse(
                id=request.id,
                result={"contents": [{"uri": uri, "mimeType": "text/plain", "text": "Log entry 1\nLog entry 2"}]}
            )
        elif uri == "stock://ticker":
             import random
             price = 100.0 + random.uniform(-5.0, 5.0)
             return JsonRpcResponse(
                id=request.id,
                result={"contents": [{"uri": uri, "mimeType": "application/json", "text": json.dumps({"price": price})}]}
            )
        else:
            return JsonRpcResponse(id=request.id, error={"code": -32602, "message": "Resource not found"})

    elif request.method == "resources/subscribe":
        # In a real server, we'd track subscriptions per connection
        # For this demo, we'll just acknowledge it and start sending updates in the SSE loop
        return JsonRpcResponse(id=request.id, result={"status": "subscribed"})
            
    return JsonRpcResponse(
        id=request.id,
        error={"code": -32601, "message": "Method not found"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)
