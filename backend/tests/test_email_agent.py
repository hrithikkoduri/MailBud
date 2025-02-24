import pytest
import pytest_asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from app.email_agent import (
    ServiceAuthenticator,
    get_threads,
    process_message,
    extract_meeting_details,
    format_meeting_details,
    ensure_rfc3339,
    create_meeting_events,
    resolve_conflicting_events,
    Message,
    Thread,
    Threads,
    MeetingDetails,
    MeetingDetailsList,
    get_threads_with_messages
)
from langchain_core.messages import HumanMessage

# At the top of the file, after imports
pytestmark = pytest.mark.asyncio

# Mock data for testing
MOCK_THREAD = {
    "id": "thread_123",
    "messages": [
        {
            "id": "msg_1",
            "snippet": "Let's schedule a meeting for tomorrow at 2 PM EST",
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Meeting Schedule"},
                    {"name": "From", "value": "sender@example.com"},
                    {"name": "To", "value": "recipient@example.com"},
                    {"name": "Date", "value": "Thu, 25 Apr 2024 10:00:00 -0400"}
                ]
            }
        }
    ]
}

MOCK_MEETING_DETAILS = MeetingDetailsList(
    meetings=[
        MeetingDetails(
            summary="Team Meeting",
            start={"dateTime": "2024-04-25T14:00:00-04:00", "timeZone": "America/New_York"},
            end={"dateTime": "2024-04-25T15:00:00-04:00", "timeZone": "America/New_York"},
            location="Online",
            description="Weekly team sync",
            attendees=["user1@example.com", "user2@example.com"]
        )
    ]
)

@pytest.fixture
def mock_credentials_file():
    with patch('os.path.exists') as mock_exists:
        mock_exists.return_value = False
        yield

@pytest_asyncio.fixture
async def mock_gmail_service():
    service = Mock()
    users_mock = Mock()
    threads_mock = Mock()
    list_mock = Mock()
    execute_mock = Mock()
    
    execute_mock.return_value = {"threads": [{"id": "thread_123"}]}
    list_mock.execute = execute_mock
    threads_mock.list = Mock(return_value=list_mock)
    users_mock.threads = Mock(return_value=threads_mock)
    service.users = Mock(return_value=users_mock)
    
    return service

@pytest_asyncio.fixture
async def mock_calendar_service():
    service = Mock()
    events_mock = Mock()
    list_mock = Mock()
    insert_mock = Mock()
    execute_list_mock = Mock()
    execute_insert_mock = Mock()
    
    execute_list_mock.return_value = {"items": []}
    execute_insert_mock.return_value = {
        "id": "event_123",
        "htmlLink": "https://calendar.google.com/event?id=123",
        "hangoutLink": "https://meet.google.com/abc-defg-hij",
        "summary": "Team Meeting",
        "start": {"dateTime": "2024-04-25T14:00:00-04:00", "timeZone": "America/New_York"},
        "end": {"dateTime": "2024-04-25T15:00:00-04:00", "timeZone": "America/New_York"},
        "location": "Online",
        "description": "Weekly team sync",
        "attendees": [{"email": "user1@example.com"}, {"email": "user2@example.com"}],
        "created": "2024-04-24T10:00:00Z",
        "updated": "2024-04-24T10:00:00Z"
    }
    
    list_mock.execute = execute_list_mock
    insert_mock.execute = execute_insert_mock
    events_mock.list = Mock(return_value=list_mock)
    events_mock.insert = Mock(return_value=insert_mock)
    service.events = Mock(return_value=events_mock)
    
    return service

@pytest.mark.asyncio
async def test_service_authenticator_initialization(mock_credentials_file):
    with patch('app.email_agent.InstalledAppFlow') as mock_flow:
        mock_flow.from_client_secrets_file.return_value = AsyncMock()
        mock_flow.from_client_secrets_file.return_value.run_local_server_async.return_value = Mock(valid=True)
        
        authenticator = ServiceAuthenticator()
        try:
            creds = await authenticator.get_credentials()
            assert creds is not None
        except Exception as e:
            pytest.fail(f"get_credentials() raised {e} unexpectedly")

@pytest.mark.asyncio
async def test_get_threads(mock_gmail_service):
    threads = await get_threads(mock_gmail_service)
    assert len(threads) == 1
    assert threads[0]["id"] == "thread_123"

@pytest.mark.asyncio
async def test_process_message():
    message = MOCK_THREAD["messages"][0]
    processed_message = await process_message(message)
    
    assert all(key in processed_message for key in ["msg_id", "msg_body", "from_", "to", "timestamp"])
    assert processed_message["msg_id"] == "msg_1"
    assert processed_message["from_"] == "sender@example.com"
    assert processed_message["to"] == ["recipient@example.com"]

@pytest.mark.asyncio
async def test_extract_meeting_details():
    mock_state = {
        "threads_with_messages": Threads(threads=[
            Thread(
                thread_id="thread_123",
                subject="Meeting Schedule",
                messages=[
                    Message(
                        msg_id="msg_1",
                        msg_body="Let's schedule a meeting for tomorrow at 2 PM EST",
                        from_="sender@example.com",
                        to=["recipient@example.com"],
                        timestamp="Thu, 25 Apr 2024 10:00:00 -0400"
                    )
                ]
            )
        ])
    }
    
    with patch('app.email_agent.llm_anthropic') as mock_llm:
        mock_llm.with_structured_output.return_value.invoke.return_value = MOCK_MEETING_DETAILS
        result = await extract_meeting_details(mock_state)
        assert "meeting_details" in result
        assert len(result["meeting_details"].meetings) == 1

@pytest.mark.asyncio
async def test_format_meeting_details():
    formatted = await format_meeting_details(MOCK_MEETING_DETAILS)
    assert isinstance(formatted, dict)
    assert "meetings" in formatted
    assert len(formatted["meetings"]) == 1
    assert "conferenceData" in formatted["meetings"][0]

@pytest.mark.asyncio
async def test_ensure_rfc3339():
    timestamp = "2024-04-25 14:00:00"
    timezone = "America/New_York"
    
    with patch('app.email_agent.llm_anthropic') as mock_llm:
        mock_llm.invoke.return_value.content = "2024-04-25T14:00:00-04:00"
        result = await ensure_rfc3339(timestamp, timezone)
        assert result == "2024-04-25T14:00:00-04:00"

@pytest.mark.asyncio
async def test_create_meeting_events(mock_calendar_service):
    mock_state = {
        "events_to_be_scheduled": {
            "meetings": [
                {
                    "summary": "Team Meeting",
                    "start": {"dateTime": "2024-04-25T14:00:00-04:00", "timeZone": "America/New_York"},
                    "end": {"dateTime": "2024-04-25T15:00:00-04:00", "timeZone": "America/New_York"},
                    "location": "Online",
                    "description": "Weekly team sync",
                    "attendees": [{"email": "user1@example.com"}, {"email": "user2@example.com"}],
                    "conferenceData": {"createRequest": {"requestId": "unique-request-id"}}
                }
            ]
        }
    }
    
    with patch('app.email_agent.calendar_service', mock_calendar_service):
        with patch('app.email_agent.ensure_rfc3339') as mock_ensure_rfc3339:
            mock_ensure_rfc3339.return_value = "2024-04-25T14:00:00-04:00"
            result = await create_meeting_events(mock_state)
            
            assert "meetings_scheduled" in result
            assert len(result["meetings_scheduled"]) == 1
            assert result["meetings_scheduled"][0]["summary"] == "Team Meeting"
            assert "event_link" in result["meetings_scheduled"][0]
            assert "meeting_link" in result["meetings_scheduled"][0]

@pytest.mark.asyncio
async def test_resolve_conflicting_events():
    mock_state = {
        "conflicting_events": [
            {
                "existing_events": [
                    {
                        "summary": "Existing Meeting",
                        "start": {"dateTime": "2024-04-25T14:00:00-04:00", "timeZone": "America/New_York"},
                        "end": {"dateTime": "2024-04-25T15:00:00-04:00", "timeZone": "America/New_York"}
                    }
                ],
                "new_event": {
                    "summary": "New Meeting",
                    "start": {"dateTime": "2024-04-25T14:00:00-04:00", "timeZone": "America/New_York"},
                    "end": {"dateTime": "2024-04-25T15:00:00-04:00", "timeZone": "America/New_York"}
                }
            }
        ],
        "meeting_details": MOCK_MEETING_DETAILS,
        "resolution_input": HumanMessage(content="Schedule all events")
    }
    
    with patch('app.email_agent.llm_anthropic') as mock_llm:
        mock_resolution = Mock()
        mock_resolution.resolved_events = MOCK_MEETING_DETAILS
        mock_resolution.resolution_description = "Conflicts resolved"
        mock_llm.with_structured_output.return_value.invoke.return_value = mock_resolution
        
        result = await resolve_conflicting_events(mock_state)
        assert "events_to_be_scheduled" in result
        assert "resolution_output" in result
        assert result["resolution_output"] == "Conflicts resolved"

@pytest.mark.asyncio
async def test_get_threads_with_messages(mock_gmail_service):
    with patch('app.email_agent.gmail_service', mock_gmail_service):
        # Mock the thread.get() response
        get_mock = Mock()
        get_mock.execute.return_value = {
            "messages": [
                {
                    "id": "msg_1",
                    "snippet": "Let's schedule a meeting",
                    "payload": {
                        "headers": [
                            {"name": "Subject", "value": "Meeting Schedule"},
                            {"name": "From", "value": "sender@example.com"},
                            {"name": "To", "value": "recipient@example.com"},
                            {"name": "Date", "value": "Thu, 25 Apr 2024 10:00:00 -0400"}
                        ]
                    }
                },
                {
                    "id": "msg_2",
                    "snippet": "Re: Let's schedule a meeting",
                    "payload": {
                        "headers": [
                            {"name": "Subject", "value": "Re: Meeting Schedule"},
                            {"name": "From", "value": "recipient@example.com"},
                            {"name": "To", "value": "sender@example.com"},
                            {"name": "Date", "value": "Thu, 25 Apr 2024 11:00:00 -0400"}
                        ]
                    }
                },
                {
                    "id": "msg_3",
                    "snippet": "Re: Let's schedule a meeting",
                    "payload": {
                        "headers": [
                            {"name": "Subject", "value": "Re: Meeting Schedule"},
                            {"name": "From", "value": "sender@example.com"},
                            {"name": "To", "value": "recipient@example.com"},
                            {"name": "Date", "value": "Thu, 25 Apr 2024 12:00:00 -0400"}
                        ]
                    }
                }
            ]
        }
        mock_gmail_service.users().threads().get = Mock(return_value=get_mock)
        
        input_state = {}
        result = await get_threads_with_messages(input_state)
        
        # Verify the result
        assert "threads_with_messages" in result
        threads = result["threads_with_messages"].threads
        assert len(threads) == 1
        assert threads[0].thread_id == "thread_123"
        assert len(threads[0].messages) == 3

@pytest.mark.asyncio
async def test_get_threads_with_messages_empty(mock_gmail_service):
    with patch('app.email_agent.gmail_service', mock_gmail_service):
        # Mock empty threads.list response
        list_mock = Mock()
        list_mock.execute.return_value = {"threads": []}
        mock_gmail_service.users().threads().list = Mock(return_value=list_mock)
        
        input_state = {}
        result = await get_threads_with_messages(input_state)
        assert "threads_with_messages" in result
        assert len(result["threads_with_messages"].threads) == 0

@pytest.mark.asyncio
async def test_get_threads_with_messages_error(mock_gmail_service):
    with patch('app.email_agent.gmail_service', mock_gmail_service):
        # Mock an error in threads.list
        list_mock = Mock()
        list_mock.execute.side_effect = Exception("API Error")
        mock_gmail_service.users().threads().list = Mock(return_value=list_mock)
        
        input_state = {}
        
        # Test error handling
        with pytest.raises(Exception) as exc_info:
            await get_threads_with_messages(input_state)
        assert "API Error" in str(exc_info.value) 