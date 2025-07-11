from fastapi import APIRouter, Request, Depends
from fastapi.responses import StreamingResponse
from open_webui.utils.auth import get_verified_user
import asyncio
import json
import threading

progress_queue = asyncio.Queue()

def update_progress(current, total):
    progress = round((current / total) * 100, 2)
    msg = {"progress": progress, "completed": current, "total": total}
    message = f"data: {json.dumps(msg)}\n\n"

    def push_to_queue():
        try:
            progress_queue.put_nowait(message)
            print(f" Queued progress: {progress}%")
        except Exception as e:
            print(" Failed to queue message:", e)

    # Use a thread to ensure it always runs outside blocking context
    threading.Thread(target=push_to_queue).start()






router = APIRouter()

@router.get("/process/file/stream")
async def process_file_stream(request: Request):
    async def event_stream():
        try:
            clear_queue(progress_queue)
            while True:
                if await request.is_disconnected():
                    print("SSE client disconnected.")
                    break
                
                try:
                    data = await asyncio.wait_for(progress_queue.get(), timeout=0.5)
                    print("sending SSE data:", data.strip())
                    yield data
                
                except asyncio.TimeoutError:
                    continue
        
        finally:
            #Clear queue once stream ends
            print("Queue Clear")
            clear_queue(progress_queue)

    return StreamingResponse(event_stream(), media_type="text/event-stream")



def clear_queue(queue: asyncio.Queue):
    try:
        while not queue.empty():
            queue.get_nowait()
            queue.task_done()
    except Exception as e:
        print("Failed to clear queue:", e)