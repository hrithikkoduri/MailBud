export interface ThreadIdResponse {
  type: 'thread_id';
  content: string;
}

export interface MessageResponse {
  type: 'message';
  content: string;
}

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

export interface EventsToScheduleResponse {
  type: 'events_to_schedule';
  data: {
    meetings: Meeting[];
  };
}

export interface FinalResponse {
  type: 'final';
  data: {
    events_to_schedule: {
      meetings: Meeting[];
    };
    conflicting_events: any[] | null;
  };
}

export interface ScheduledMeeting {
  summary: string;
  event_link: string;
  meeting_link: string;
  start: string;
  end: string;
  timezone: string;
  location: string;
  description: string;
  attendees: string[];
  created_at: string;
  updated_at: string;
}

export interface MeetingsScheduledResponse {
  type: 'meetings_scheduled';
  data: {
    meetings: ScheduledMeeting[];
  };
}

export type StreamResponse =
  | ThreadIdResponse
  | MessageResponse
  | EventsToScheduleResponse
  | FinalResponse
  | MeetingsScheduledResponse; 