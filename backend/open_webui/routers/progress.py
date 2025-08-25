from fastapi import APIRouter, Request, Depends
from fastapi.responses import StreamingResponse
from open_webui.utils.auth import get_verified_user
import asyncio
import json
import threading

progress_queue = asyncio.Queue()
stop_event = asyncio.Event()

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

def triggerStop():
    stop_event.set()

def getStop():
    return stop_event.is_set()

def resetStop():
    stop_event.clear()

router = APIRouter()

#Sends embedding progress to the front end
@router.get("/process/file/stream")
async def process_file_stream(request: Request):
    async def event_stream():
        try:
            clear_queue(progress_queue)
            while True:
                if await request.is_disconnected():
                    print("SSE client disconnected.")
                    break
                if getStop():
                    print("Embedding has been canceled.")
                    break
                try:
                    data = await asyncio.wait_for(progress_queue.get(), timeout=0.1)
                    print("sending SSE data:", data.strip())
                    yield data
                
                except asyncio.TimeoutError:
                    continue
        
        finally:
            #Clear queue once stream ends
            clear_queue(progress_queue)
    return StreamingResponse(event_stream(), media_type="text/event-stream")

#Function called from knowledge end while embedding router
#Throws an error in the embedding loop
def endWhileRun():
    triggerStop()
    clear_queue(progress_queue)


#Clears the queue in order to not mess up later functionaility
def clear_queue(queue: asyncio.Queue):
    try:
        while not queue.empty():
            print("Queue Clear")
            queue.get_nowait()
            queue.task_done()
    except Exception as e:
        print("Failed to clear queue:", e)