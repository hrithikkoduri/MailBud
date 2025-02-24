export interface Meeting {
  summary: string;
  start: {
    dateTime: string;
    timeZone: string;
  };
  end: {
    dateTime: string;
    timeZone: string;
  };
  location: string;
  attendees: string[];
}

export interface ConflictingEvent {
  summary: string;
  start: {
    dateTime: string;
    timeZone: string;
  };
  end: {
    dateTime: string;
    timeZone: string;
  };
  location: string;
  description: string;
  attendees: { email: string }[];
}

export interface MeetingsData {
  newMeetings: Meeting[];
  conflictingEvents: {
    existing_events: ConflictingEvent[];
    new_event: Meeting;
  }[];
} 