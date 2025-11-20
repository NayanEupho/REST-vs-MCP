import time
import asyncio
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="REST Server")

class EchoRequest(BaseModel):
    message: str

class CalculateRequest(BaseModel):
    operation: str
    a: float
    b: float

@app.get("/status")
async def status():
    return {"status": "ok", "timestamp": time.time()}

@app.post("/echo")
async def echo(request: EchoRequest):
    return {"message": request.message, "timestamp": time.time()}

@app.post("/tools/calculate")
async def calculate(request: CalculateRequest):
    # Simulate some computation time
    await asyncio.sleep(0.01) 
    
    if request.operation == "add":
        result = request.a + request.b
    elif request.operation == "subtract":
        result = request.a - request.b
    elif request.operation == "multiply":
        result = request.a * request.b
    elif request.operation == "divide":
        if request.b == 0:
            raise HTTPException(status_code=400, detail="Division by zero")
        result = request.a / request.b
    else:
        raise HTTPException(status_code=400, detail="Unknown operation")
        
    return {"result": result, "operation": request.operation}

@app.get("/context")
async def get_context(size: int = 1000):
    # Simulate retrieving a large context (e.g., for RAG)
    # Generate a string of 'size' bytes
    data = "x" * size
    return {"data": data, "size": size}

class ChatRequest(BaseModel):
    history: List[Dict[str, str]]
    message: str

class TaskRequest(BaseModel):
    complexity: int

# In-memory task store
tasks: Dict[str, Dict[str, Any]] = {}

@app.post("/chat")
async def chat(request: ChatRequest):
    # Simulate processing full history
    # In a real LLM, processing time scales with context length
    # We simulate this by sleeping proportional to history length
    context_length = sum(len(m["content"]) for m in request.history) + len(request.message)
    delay = context_length * 0.0001 # 0.1ms per char
    await asyncio.sleep(delay)
    
    response = f"Echo: {request.message} (Context: {len(request.history)} msgs)"
    return {"response": response, "usage": context_length}

@app.post("/tasks/generate")
async def generate_task(request: TaskRequest):
    task_id = str(time.time())
    tasks[task_id] = {"status": "pending", "progress": 0, "result": None}
    
    # Start background task
    asyncio.create_task(run_background_task(task_id, request.complexity))
    
    return {"task_id": task_id}

@app.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    return tasks[task_id]

@app.get("/resources/stock")
async def get_stock_price():
    # Simulate a volatile stock
    import random
    price = 100.0 + random.uniform(-5.0, 5.0)
    return {"symbol": "MCP", "price": round(price, 2), "timestamp": time.time()}

    return {"symbol": "MCP", "price": round(price, 2), "timestamp": time.time()}

class StepRequest(BaseModel):
    input_data: str

@app.post("/workflow/step1")
async def step1(request: StepRequest):
    # Step 1: Data Ingestion (Fast)
    await asyncio.sleep(0.05)
    return {"output": f"Processed({request.input_data})", "step": 1}

@app.post("/workflow/step2")
async def step2(request: StepRequest):
    # Step 2: Analysis (Medium)
    await asyncio.sleep(0.1)
    return {"output": f"Analyzed({request.input_data})", "step": 2}

@app.post("/workflow/step3")
async def step3(request: StepRequest):
    # Step 3: Summarization (Slow)
    await asyncio.sleep(0.2)
    return {"output": f"Summary({request.input_data})", "step": 3}

async def run_background_task(task_id: str, complexity: int):
    for i in range(10):
        await asyncio.sleep(0.1 * complexity)
        tasks[task_id]["progress"] = (i + 1) * 10
        
    tasks[task_id]["status"] = "completed"
    tasks[task_id]["result"] = "Task Completed Successfully"
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
