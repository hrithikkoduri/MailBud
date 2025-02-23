from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any
import uuid
import json
from app.email_agent import get_email_agent
import asyncio

app = FastAPI()

# Store the email agent instance
email_agent = None

@app.on_event("startup")
async def startup_event():
    """Initialize the email agent when the application starts"""
    global email_agent
    email_agent = await get_email_agent()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ResolutionInput(BaseModel):
    resolution: str

def format_message(message):
    """Extract just the content from a message object"""
    if hasattr(message, 'content'):
        return message.content
    return str(message)

async def stream_events_generator(input_message, config):
    try:
        if email_agent is None:
            raise HTTPException(status_code=500, detail="Email agent not initialized")
            
        # Send thread_id first
        yield json.dumps({
            "type": "thread_id",
            "content": config["configurable"]["thread_id"]
        }, indent=2) + "\n\n"
            
        events_to_schedule = None
        async for event in email_agent.astream({"messages": input_message}, config, stream_mode="values"):
            # Stream each event as it occurs
            if "messages" in event:
                messages = event["messages"]
                # Get only the latest message
                latest_message = messages[-1] if isinstance(messages, list) else messages
                formatted_message = format_message(latest_message)
                yield json.dumps({
                    "type": "message",
                    "content": formatted_message
                }, indent=2) + "\n\n"
            
            if "events_to_be_scheduled" in event:
                events_to_schedule = event["events_to_be_scheduled"]
                yield json.dumps({
                    "type": "events_to_schedule",
                    "data": {
                        "meetings": [
                            {
                                "summary": meeting["summary"],
                                "start": meeting["start"],
                                "end": meeting["end"],
                                "location": meeting["location"],
                                "attendees": meeting["attendees"]
                            } for meeting in events_to_schedule["meetings"]
                        ]
                    }
                }, indent=2) + "\n\n"
            
            if "conflicting_events" in event:
                final_data = {
                    "type": "final",
                    "data": {
                        "events_to_schedule": events_to_schedule,
                        "conflicting_events": None if event["conflicting_events"] == "NONE" else event["conflicting_events"]
                    }
                }
                yield json.dumps(final_data, indent=2) + "\n\n"
    except Exception as e:
        yield json.dumps({"type": "error", "data": str(e)}, indent=2) + "\n\n"

async def schedule_events_generator(config):
    try:
        if email_agent is None:
            raise HTTPException(status_code=500, detail="Email agent not initialized")
            
        async for event in email_agent.astream(None, config, stream_mode="values"):
            if "messages" in event:
                messages = event["messages"]
                latest_message = messages[-1] if isinstance(messages, list) else messages
                formatted_message = format_message(latest_message)
                yield json.dumps({
                    "type": "message",
                    "content": formatted_message
                }, indent=2) + "\n\n"
            
            if "meetings_scheduled" in event:
                yield json.dumps({
                    "type": "meetings_scheduled",
                    "data": {
                        "meetings": [
                            {
                                "summary": meeting["summary"],
                                "event_link": meeting["event_link"],
                                "meeting_link": meeting["meeting_link"],
                                "start": meeting["start"],
                                "end": meeting["end"],
                                "timezone": meeting["timezone"],
                                "location": meeting["location"],
                                "description": meeting["description"],
                                "attendees": meeting["attendees"],
                                "created_at": meeting["created_at"],
                                "updated_at": meeting["updated_at"]
                            } for meeting in event["meetings_scheduled"]
                        ]
                    }
                }, indent=2) + "\n\n"
            
            await asyncio.sleep(2)
    except Exception as e:
        yield json.dumps({"type": "error", "data": str(e)}, indent=2) + "\n\n"

@app.get("/api/fetch-meetings")
async def fetch_meetings():
    # Generate unique thread ID
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    
    input_message = ["Check Email Threads to schedule meetings"]
    
    return StreamingResponse(
        stream_events_generator(input_message, config),
        media_type="text/event-stream"
    )

@app.post("/api/schedule-meetings/{thread_id}")
async def schedule_meetings(thread_id: str, resolution_input: ResolutionInput):
    config = {"configurable": {"thread_id": thread_id}}
    
    # Update state with resolution input
    await email_agent.aupdate_state(config, {
         "resolution_input": resolution_input.resolution
    })

    return StreamingResponse(
        schedule_events_generator(config),
        media_type="text/event-stream"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)