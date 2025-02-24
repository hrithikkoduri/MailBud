from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
import os
import os.path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from pydantic import BaseModel, Field
from typing import List, Annotated , TypedDict, Literal, Dict
from operator import add
from langgraph.graph import MessagesState
from langchain_core.messages import HumanMessage, SystemMessage
import json
from dateutil.parser import parse
from datetime import datetime
from langgraph.graph import START, END, StateGraph
import sqlite3
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
import aiosqlite
import aiohttp
from google.auth.transport.requests import AuthorizedSession
import asyncio
from functools import partial



async def get_memory():
    conn = await aiosqlite.connect(":memory:")
    return AsyncSqliteSaver(conn)

load_dotenv()
def set_env_vars(var):
    value = os.getenv(var)
    if value is not None:
        os.environ[var] = value


vars = ["OPENAI_API_KEY", "LANGCHAIN_API_KEY", "LANGCHAIN_TRACING_V2", "LANGCHAIN_ENDPOINT", "LANGCHAIN_PROJECT", "TAVILY_API_KEY", "ANTHROPIC_API_KEY"]

for var in vars:
    set_env_vars(var)

llm_4o = ChatOpenAI(model="gpt-4o", temperature=0)
llm_o3_mini = ChatOpenAI(model="o3-mini", reasoning_effort="high")

llm_anthropic = ChatAnthropic(model="claude-3-5-sonnet-20240620", temperature=0)
llm = llm_4o



SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/calendar.events.readonly"
]

class ServiceAuthenticator:
    def __init__(self, credentials_path='credentials.json', token_path='token.json'):
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.creds = self.get_credentials()
        
    async def get_credentials(self):
        """Gets valid user credentials from storage or initiates OAuth2 flow."""
        creds = None
        
        if os.path.exists(self.token_path):
            try:
                creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
            except Exception as e:
                print(f"Error loading existing credentials: {e}")
                
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    print(f"Error refreshing credentials: {e}")
                    creds = None
            
            if not creds:
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, SCOPES)
                    creds = await flow.run_local_server_async(
                        port=0,
                        success_message='Authentication successful! You can close this window.',
                        authorization_prompt_message='Please authorize the application.'
                    )
                except Exception as e:
                    raise Exception(f"Failed to authenticate: {e}")
                
                # Save the credentials for the next run
                try:
                    with open(self.token_path, 'w') as token:
                        token.write(creds.to_json())
                except Exception as e:
                    print(f"Warning: Could not save credentials: {e}")
                    
        return creds

    async def get_gmail_service(self):
        """Returns an authorized Gmail API service instance."""
        creds = await self.get_credentials()
        return build('gmail', 'v1', credentials=creds)

    async def get_calendar_service(self):
        """Returns an authorized Calendar API service instance."""
        creds = await self.get_credentials()
        return build('calendar', 'v3', credentials=creds)


class Message(TypedDict):
    msg_id: str
    msg_body: str
    from_: str  = Field(alias="from")
    to: List[str]
    timestamp: str
    

class Thread(BaseModel):
    thread_id: str
    subject: str
    messages: Annotated[List[Message], Field(description="List of messages in the thread"), add]

class Threads(BaseModel):
    threads: Annotated[List[Thread], Field(description="List of threads"), add]


class Date(BaseModel):
    dateTime: str
    timeZone: str


class MeetingDetails(BaseModel):
    summary: str
    start: Date
    end: Date
    location: str
    description: str
    attendees: List[str] = Field(description="The list of email addresses of the attendees, in the format: [\"email@example.com\", \"email2@example.com\"]")
    

class MeetingDetailsList(BaseModel):
    meetings: Literal["NONE"] | List[MeetingDetails]

class ConflictingEvents(TypedDict):
    existing_event: Literal["NONE"] | List[Dict]
    new_event: List[Dict]

class Resolution(BaseModel):
    resolved_events: MeetingDetailsList
    resolution_description: str = Field(description="A description of the conflicting events were resolved based on the users input")

class AgentState(MessagesState):
    threads_with_messages: Threads
    meeting_details: MeetingDetailsList
    meetings_scheduled: List[Dict]
    events_to_be_scheduled: List[Dict]
    conflicting_events: List[ConflictingEvents]
    resolution_input: HumanMessage
    
gmail_service = []
calendar_service = []

async def complete_auth(state: AgentState):
    global gmail_service, calendar_service
    auth = ServiceAuthenticator()
    gmail_service = await auth.get_gmail_service()
    calendar_service = await auth.get_calendar_service()
    return {"messages": ["Google account authenticated to access Gmail and Calendar, Fetching email threads from Gmail inbox..."]}



async def get_threads(gmail_service):
    try:
        
        loop = asyncio.get_event_loop()
        threads = await loop.run_in_executor(
            None, 
            partial(gmail_service.users().threads().list(userId="me", maxResults=50).execute)
        )
        return threads.get("threads", [])
    except HttpError as error:
        print(f"An error occurred: {error}")

async def get_subject(message):
    # Get headers from payload
    headers = message.get('payload', {}).get('headers', [])
    
    # Find the subject header
    for header in headers:
        if header['name'].lower() == 'subject':
            return header['value']
    
    return None

async def get_from(message):
    headers = message.get('payload', {}).get('headers', [])
    for header in headers:
        if header['name'].lower() == 'from':
            return header['value']
    return None

async def get_to(message):
    headers = message.get('payload', {}).get('headers', [])
    to = []
    for header in headers:
        if header['name'].lower() == 'to':
            to.append(header['value'])
        if header['name'].lower() == 'cc':
            to.append(header['value'])
    return to

async def get_timestamp(message):
    headers = message.get('payload', {}).get('headers', [])
    for header in headers:
        if header['name'].lower() == 'date':
            return header['value']
    return None

async def process_message(message) -> Message:
    msg_id = message["id"]
    msg_body = message.get("snippet", "")
    sender = await get_from(message)
    recipients = await get_to(message)
    timestamp = await get_timestamp(message)
    return Message(
        msg_id=msg_id,
        msg_body=msg_body,
        from_=sender,
        to=recipients,
        timestamp=timestamp
    )

async def get_threads_with_messages(state: AgentState):
    global gmail_service
    threads_with_messages = Threads(threads=[])
    try:
        service = gmail_service
        print("Getting threads")
        threads = await get_threads(gmail_service)
        print("Threads retrieved : ", threads)
        
        for thread in threads:
            thread_id = thread["id"]
            
            # Get thread data in a single API call
            loop = asyncio.get_event_loop()
            tdata = await loop.run_in_executor(
                None, 
                partial(service.users().threads().get(
                    userId="me", 
                    id=thread["id"], 
                    format='full' 
                ).execute)
            )
            print("Thread data retrieved ")
            
            if len(tdata["messages"]) > 2: 
                
                messages = await asyncio.gather(*(process_message(message) for message in tdata["messages"]))


                subject = await get_subject(tdata["messages"][0])
                threads_with_messages.threads.append(
                    Thread(thread_id=thread_id, subject=subject, messages=messages)
                )

        return {"threads_with_messages": threads_with_messages, "messages" : ["Email threads with messages retrieved, extracting meeting details..."]}
    
    except HttpError as error:
        return {f"An error occurred: {error}"}



async def extract_meeting_details(state: AgentState):

    system_message = """
    You are an intelligent assistant for an email agent that extracts meeting details from a list of email threads.

    ### Input:
    You will receive:
    - A list of email threads, where each thread includes:
    - A thread ID
    - A subject line
    - A list of messages, with each message containing:
        - Message ID
        - Message body (contains meeting details)
        - Sender email (message from)
        - Recipient emails (message to)
        - Timestamp (including UTC offset)
    - The current date and time in ISO 8601 format

    ### Extraction Guidelines:
    1. **Meeting Detection**:
    - Extract meeting details only if they are explicitly mentioned.
    - If no meeting details are found, return **NONE**.
    - Ignore past meetings; only return upcoming meetings based on the current date and time.

    2. **Timezone Handling**:
    - Determine the timezone using the timestamp of the message containing meeting details.
    - The UTC offset in the timestamp (e.g., "-0700") should be mapped to its corresponding region format, such as `"America/Phoenix"` or `"America/New_York"`.

    3. **Meeting Duration**:
    - If the meeting duration or end time is not specified, assume a default duration of **30 minutes**.

    4. **Attendee Emails**:
    - Carefully extract attendee emails without any typos or errors.

    5. **Meeting Location**:
    - If a location is explicitly mentioned in the email, use it.
    - If no location is provided, assume the meeting is **Online**.

    6. **Attendee Emails**:
    - Carefully extract attendee emails without any typos or errors,in the format:
       ["email1@example.com",  "email12@example.com"]

    Ensure accuracy and completeness in extracting the details.
    """
    human_prompt = """
    Extract the meeting details from the following thread of emails:
    {threads_with_messages}

    Here is the current date and time:
    {current_date_time}
    """
    threads_with_messages = state["threads_with_messages"]
    threads_with_messages = threads_with_messages.threads
    current_date_time = datetime.now().isoformat()

    human_message = human_prompt.format(threads_with_messages=threads_with_messages, current_date_time=current_date_time)
    messages = [SystemMessage(content=system_message), HumanMessage(content=human_message)]

    meeting_details = llm_anthropic.with_structured_output(MeetingDetailsList).invoke(messages)

    if meeting_details == "NONE":
        return {"messages" : ["No meeting details found in the email threads."]}
    else:
        return {"meeting_details" : meeting_details, "messages" : ["Extracted meeting details from the email threads, creating meeting events to be scheduled..."]}

    
async def after_extract_meeting_details_router(state:AgentState):
    meeting_details = state["meeting_details"]

    if meeting_details == "NONE":
        return "no_meeting_details"
    else:
        return "events_to_schedule"
    

async def format_meeting_details(meeting_details):
    """
    Takes a result object containing meetings, formats them into JSON,
    and returns a dictionary of meetings.
    Args:
        result: Object containing meetings data
    
    Returns:
        dict: Formatted meetings data as a dictionary
    """
   
    json_output = meeting_details.model_dump_json(indent=2)
    dict_output = json.loads(json_output)
    print("--------------------------------")
    print(dict_output)
    print

    
    
    # Display all meetings
    print("All scheduled meetings:")
    print("======================")
    for meeting in dict_output["meetings"]:
        meeting["conferenceData"] = {"createRequest": {"requestId": "unique-request-id"}}

        if meeting["attendees"] is not None:
            meeting["attendees"] = [{"email" : email} for email in meeting["attendees"]]
        print(meeting)
        print("--------------------------------")
    
    return dict_output


async def events_to_schedule(state: AgentState):
    meeting_details = state["meeting_details"]

    print("--------------------------------")
    print("Creating meeting events")
    print(meeting_details)
    print("--------------------------------")

    formatted_meeting_details = await format_meeting_details(meeting_details)
    print("Formatted meeting details")
    print(formatted_meeting_details)
    print("--------------------------------")

    return {"events_to_be_scheduled" : formatted_meeting_details, "messages" : ["Created meeting events to be scheduled, fetching conflicting events..."]}



async def ensure_rfc3339(timestamp_str, timezone):
    system_message = """
    Parse the input timestamp and return it in RFC3339 format.
    If the timestamp is naive (i.e. has no timezone), assume UTC.

    ### Input:
    - A timestamp string
    - A timezone string

    ### Output:
    - A timestamp string in RFC3339 format
    """
    human_prompt = """
    This is the timestamp string:
    {timestamp_str}
    This is the timezone string:
    {timezone}

    Return the timestamp string in RFC3339 format only, nothing else.
    """
    human_prompt = human_prompt.format(timestamp_str=timestamp_str, timezone=timezone)
    messages = [SystemMessage(content=system_message), HumanMessage(content=human_prompt)]
    response = llm_anthropic.invoke(messages)
    return response.content


async def fetch_conflicting_events_for_meeting(state: AgentState):
    """
    Fetch any existing calendar events that conflict with the given meeting_event.
    """
    global calendar_service
    calendar_id = "primary"
    conflicting_events = []
    bool_conflicting_events = False
    for meeting_event in state["events_to_be_scheduled"]["meetings"]:
         # Extract start and end times from the meeting event
        time_min_raw = meeting_event["start"]["dateTime"]

        time_max_raw = meeting_event["end"]["dateTime"]
        timezone = meeting_event["start"]["timeZone"]

        # Ensure the timestamps are RFC3339 compliant
        time_min = await ensure_rfc3339(time_min_raw, timezone)
        time_max = await ensure_rfc3339(time_max_raw, timezone)

        print(time_min, time_max)
        type(time_min)
        type(time_max)
        

        # Query the calendar for events in the specified time range
        loop = asyncio.get_event_loop()
        events_result = await loop.run_in_executor(
            None, 
            partial(calendar_service.events().list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy="startTime"
            ).execute)
        )
        existing_events = []
        print(events_result)
        for event in events_result.get("items", []):
            existing_event = {
                "summary": event.get("summary", "No summary"),
                "start": {
                "dateTime": event.get("start", {}).get("dateTime"),
                "timeZone": event.get("start", {}).get("timeZone")
            },
            "end": {
                "dateTime": event.get("end", {}).get("dateTime"), 
                "timeZone": event.get("end", {}).get("timeZone")
            },
            "location": event.get("location", "No location"),
            "description": event.get("description", "No description"),
            "attendees": [{"email" : attendee.get("email", "No email")} for attendee in event.get("attendees", [])]
            }
            existing_events.append(existing_event)

        if existing_events != []:
            bool_conflicting_events = True

        print(existing_events)
        print("--------------------------------")
        conflicting_events.append(ConflictingEvents(existing_events=existing_events, new_event=meeting_event))
    
    
    if bool_conflicting_events == False:
        return {"conflicting_events" : "NONE", "messages" : ["No conflicting events found. Will collect any updates for the events before scheduling them..."], "events_to_be_scheduled" : state["events_to_be_scheduled"]}
    else:
        return {"conflicting_events" : conflicting_events, "messages" : ["Found conflicting events, need to resolve them..."], "events_to_be_scheduled" : state["events_to_be_scheduled"]}




async def resolve_conflicting_events(state: AgentState):

        
        system_message = """
        You are an intelligent assistant for an email agent that resolves conflicts in calendar events.

        ### Input:
        You will receive:
        - A list of conflicting events, where each event includes:
            - Existing events
            - New event
        - A list of events to be scheduled
        - Users Input regarding the resolution of the conflicts

        Based on the users input, you need to resolve the conflicts and return the events to be scheduled.

        ### Output:
        The output of the resolved events to be scheduled. It should be in the same format as the events_to_be_scheduled.
        """
        human_prompt = """
        This is the list of conflicting events:
        {conflicting_events}
        \n\n
        This is the list of events to be scheduled:
        {meeting_details}
        \n\n
        This is the users input regarding the resolution of the conflicts:
        {user_input}
        """
        conflicting_events = state["conflicting_events"]
        meeting_details = state["meeting_details"]
        resolution_input = state["resolution_input"]

        human_message = human_prompt.format(conflicting_events=conflicting_events, meeting_details=meeting_details, user_input=resolution_input)

        messages = [SystemMessage(content=system_message), HumanMessage(content=human_message)]
        resolution = llm_anthropic.with_structured_output(Resolution).invoke(messages)
        resolved_events = resolution.resolved_events
        resolution_description = resolution.resolution_description
        formatted_resolved_events = await format_meeting_details(resolved_events)
        
        return {"events_to_be_scheduled" : formatted_resolved_events, "messages" : [resolution_description]}

    

async def create_meeting_events(state: AgentState):
    calendar_id = "primary"

    global calendar_service
    
    events_to_be_scheduled = state["events_to_be_scheduled"]

    meetings_scheduled = []
    for meeting_event in events_to_be_scheduled["meetings"]:
        # --- Check for and delete conflicting events ---
        time_min = meeting_event["start"]["dateTime"]
        time_max = meeting_event["end"]["dateTime"]
        timezone = meeting_event["start"]["timeZone"]

        time_min = await ensure_rfc3339(time_min, timezone)
        time_max = await ensure_rfc3339(time_max, timezone)

        # Fetch conflicting events within the meeting's time range
        loop = asyncio.get_event_loop()
        events_result = await loop.run_in_executor(
            None, 
            partial(calendar_service.events().list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy="startTime"
            ).execute)
        )

        conflicting_events = events_result.get("items", [])
        if conflicting_events:
            print(f"Found {len(conflicting_events)} conflicting event(s) for meeting '{meeting_event.get('summary', 'Unnamed Meeting')}':")
            for conflict in conflicting_events:
                event_id = conflict["id"]
                conflict_summary = conflict.get("summary", event_id)
                # Delete the conflicting event
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None, 
                    partial(calendar_service.events().delete(
                        calendarId=calendar_id, 
                        eventId=event_id).execute)
                )
                print(f"Deleted conflicting event: {conflict_summary}")
            print("--------------------------------")
        else:
            print(f"No conflicts for meeting '{meeting_event.get('summary', 'Unnamed Meeting')}'.")
            print("--------------------------------")

        # --- Create the new event ---
        loop = asyncio.get_event_loop()
        created_event = await loop.run_in_executor(
            None, 
            partial(calendar_service.events().insert(
                calendarId=calendar_id,
                body=meeting_event,
                conferenceDataVersion=1,
                sendUpdates="all"
            ).execute)
        )


        event_scheduled = {
            "summary": created_event['summary'],
            "event_link": created_event.get('htmlLink'),
            "meeting_link": created_event['hangoutLink'],
            "start": created_event['start']['dateTime'],
            "end": created_event['end']['dateTime'],
            "timezone": created_event['start']['timeZone'],
            "location": created_event['location'],
            "description": created_event['description'],
            "attendees": [", ".join([attendee['email'] for attendee in created_event['attendees']])],
            "created_at": created_event['created'],
            "updated_at": created_event['updated']
        }
        print(event_scheduled)
        meetings_scheduled.append(event_scheduled)

    
    return {"meetings_scheduled" : meetings_scheduled, "messages" : ["Created meeting events in the calendar and sent notifications to the attendees!"]}


async def no_meeting_details(state: AgentState):

    return {"messages": ["No meeting details found!"]}
    

builder = StateGraph(AgentState)

builder.add_node("complete_auth",complete_auth)
builder.add_node("get_threads_with_messages", get_threads_with_messages)
builder.add_node("extract_meeting_details", extract_meeting_details)
builder.add_node("events_to_schedule", events_to_schedule)
builder.add_node("create_meeting_events", create_meeting_events)
builder.add_node("no_meeting_details", no_meeting_details)
builder.add_node("resolve_conflicting_events", resolve_conflicting_events)
builder.add_node("fetch_conflicting_events_for_meeting", fetch_conflicting_events_for_meeting)

builder.add_edge(START, "complete_auth")
builder.add_edge("complete_auth", "get_threads_with_messages")
builder.add_edge("get_threads_with_messages", "extract_meeting_details")
builder.add_conditional_edges("extract_meeting_details", after_extract_meeting_details_router,["no_meeting_details","events_to_schedule"])
builder.add_edge("events_to_schedule", "fetch_conflicting_events_for_meeting")
builder.add_edge("fetch_conflicting_events_for_meeting", "resolve_conflicting_events")
builder.add_edge("resolve_conflicting_events", "create_meeting_events")
builder.add_edge("create_meeting_events", END)
builder.add_edge("no_meeting_details", END)


async def get_email_agent():
    memory = await get_memory()
    return builder.compile(checkpointer=memory, interrupt_before=["resolve_conflicting_events"])

# Export the get_email_agent function
__all__ = ['get_email_agent']

# Remove any direct email_agent instantiation at module level

