'use client';

import { useState } from 'react';
import { StreamResponse, FinalResponse } from '@/types/api';
import { MeetingsData } from '@/types/meetings';
import { format } from 'date-fns';

export default function Home() {
  const [currentMessage, setCurrentMessage] = useState<string | null>(null);
  const [threadId, setThreadId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [streamingComplete, setStreamingComplete] = useState(false);
  const [meetingsData, setMeetingsData] = useState<MeetingsData | null>(null);
  const [resolutionInput, setResolutionInput] = useState<string>('');
  const [selectedEvents, setSelectedEvents] = useState<Set<string>>(new Set());
  const [selectAll, setSelectAll] = useState(false);
  const [replaceConflicting, setReplaceConflicting] = useState<Set<string>>(new Set());
  const [displayInput, setDisplayInput] = useState<Map<string, string>>(new Map());

  const handleStreamMessage = (message: string) => {
    setCurrentMessage(message);
  };

  const formatDateTime = (dateTime: string) => {
    return format(new Date(dateTime), 'MMM d, yyyy h:mm a');
  };

  const handleFinalResponse = (data: FinalResponse['data']) => {
    if (data.conflicting_events === "NONE" || !data.conflicting_events) {
      setMeetingsData({
        newMeetings: data.events_to_schedule.meetings,
        conflictingEvents: []
      });
    } else {
      setMeetingsData({
        newMeetings: data.conflicting_events.map(ce => ce.new_event),
        conflictingEvents: data.conflicting_events
      });
    }
  };

  const handleResolution = async (resolution: string) => {
    if (!resolution.trim() && selectedEvents.size > 0) {
      alert('Please enter a resolution suggestion');
      return;
    }
    
    // TODO: Implement the resolution handling logic for multiple events
    console.log(`Resolution for selected events:`, Array.from(selectedEvents));
    console.log(`Resolution text:`, resolution);
    setResolutionInput(''); // Clear input after submission
  };

  const fetchMeetings = async () => {
    setLoading(true);
    setCurrentMessage(null);
    
    try {
      // Initial authentication message
      

      const response = await fetch('http://localhost:8000/api/fetch-meetings');
      const reader = response.body?.getReader();
      
      if (!reader) return;

      let emailThreadsRetrieved = false;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = new TextDecoder().decode(value);
        const events = chunk.split('\n\n').filter(Boolean);

        for (const event of events) {
          const data: StreamResponse = JSON.parse(event);
          
          switch (data.type) {
            case 'thread_id':
              setThreadId(data.content);
              break;
            case 'message':
              handleStreamMessage(data.content);
              await new Promise(resolve => setTimeout(resolve, 2000));
              break;
            case 'final':
              handleFinalResponse(data.data);
              break;
          }
        }
      }
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setLoading(false);
      setStreamingComplete(true);
    }
  };

  return (
    <main className="min-h-screen bg-[conic-gradient(at_top,_var(--tw-gradient-stops))] from-blue-100 via-purple-50 to-rose-100">
      <div className="absolute inset-0 bg-grid-slate-200 [mask-image:linear-gradient(0deg,white,rgba(255,255,255,0.6))] bg-[size:20px_20px]" />
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="w-96 h-96 bg-blue-500/10 rounded-full blur-3xl animate-pulse" />
        <div className="w-96 h-96 bg-purple-500/10 rounded-full blur-3xl animate-pulse delay-700" />
      </div>
      
      <div className="relative">
        <div className="w-full px-4 py-8 space-y-8">
          <div className="text-center space-y-4">
            <div className="inline-block">
              <h1 className="text-6xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-600 via-purple-600 to-pink-600 animate-gradient">
                MailBud
              </h1>
              <div className="h-1 w-full bg-gradient-to-r from-blue-600 via-purple-600 to-pink-600 rounded-full transform scale-x-0 animate-expand" />
            </div>
            <p className="text-slate-600 text-lg font-light">
              Your AI assistant that helps manage your inbox and schedule meetings effortlessly
            </p>
          </div>
          
          <div className="bg-white/90 backdrop-blur-lg rounded-3xl shadow-xl p-8 space-y-6 border border-white/20 w-[98%] max-w-[1100px] mx-auto">
            {!streamingComplete ? (
              <button
                onClick={fetchMeetings}
                disabled={loading}
                className="w-full px-6 py-4 bg-gradient-to-r from-blue-500 via-blue-600 to-blue-700 text-white rounded-2xl 
                  hover:from-blue-600 hover:via-blue-700 hover:to-blue-800 disabled:opacity-50 transition-all duration-300 
                  shadow-lg shadow-blue-500/20 hover:shadow-xl hover:shadow-blue-500/30 hover:-translate-y-0.5"
              >
                {loading ? (
                  <span className="flex items-center justify-center space-x-2">
                    <svg className="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    <span>{currentMessage || 'Processing...'}</span>
                  </span>
                ) : 'Fetch Meetings'}
              </button>
            ) : (
              <div className="space-y-6">
                <div className="text-center animate-fadeIn">
                  <h2 className="text-lg bg-clip-text text-transparent bg-gradient-to-r from-blue-600 via-purple-600 to-pink-600">
                    Found following meetings to be scheduled from email threads:
                  </h2>
                </div>

                {meetingsData && (
                  <div className="space-y-6">
                    <div className="flex items-center gap-4 px-4">
                      <div className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          checked={selectAll}
                          onChange={(e) => {
                            setSelectAll(e.target.checked);
                            if (e.target.checked) {
                              setSelectedEvents(new Set(meetingsData.newMeetings.map(m => m.summary)));
                              const newResolution = resolutionInput + "\n---------------------------------\n\nSchedule all events\n\n---------------------------------\n";
                              setResolutionInput(newResolution);
                              console.log("Resolution input updated:", newResolution);
                            } else {
                              setSelectedEvents(new Set());
                              const newResolution = resolutionInput.replace("\n---------------------------------\n\nSchedule all events\n\n---------------------------------\n", "");
                              setResolutionInput(newResolution);
                              console.log("Resolution input updated:", newResolution);
                            }
                          }}
                          className="h-5 w-5 rounded border-gray-300 text-purple-600 focus:ring-purple-500"
                        />
                        <label className="text-sm font-medium text-slate-600">Select All Events</label>
                      </div>
                      <span className="text-sm text-slate-500 italic">
                        (The default resolution setting is to replace all conflicting events if any present)
                      </span>
                    </div>
                    {meetingsData.newMeetings.map((meeting, index) => {
                      const relatedConflicts = meetingsData.conflictingEvents?.find(
                        conflict => conflict.new_event.summary.toLowerCase() === meeting.summary.toLowerCase()
                      );

                      return (
                        <div key={index} className="bg-white/90 backdrop-blur-sm rounded-xl px-3 py-3 shadow-xl border border-white/20">
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-12 px-4 py-4">
                            {/* New Meeting Column */}
                            <div>
                              <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-6">New Meeting</h3>
                              <div className="bg-white/80 backdrop-blur-sm rounded-xl p-4 shadow-md border border-white/20">
                                <div className="flex justify-between items-start">
                                  <h4 className="font-medium text-slate-800 text-xl">{meeting.summary}</h4>
                                  <input
                                    type="checkbox"
                                    checked={selectedEvents.has(meeting.summary)}
                                    onChange={(e) => {
                                      const newSelected = new Set(selectedEvents);
                                      const meetingDetails = `
                                        Summary: ${meeting.summary}
                                        Time: ${formatDateTime(meeting.start.dateTime)} - ${formatDateTime(meeting.end.dateTime)}
                                        Location: ${meeting.location || 'No location specified'}
                                        Attendees: ${meeting.attendees.map(a => a.email).join(', ')}
                                      `;
                                      const scheduleString = `\n---------------------------------\n\nSchedule the new meeting:\n${meetingDetails}\n\n---------------------------------\n`;

                                      if (e.target.checked) {
                                        newSelected.add(meeting.summary);
                                        const newResolution = resolutionInput + scheduleString;
                                        setResolutionInput(newResolution);
                                        console.log("Resolution input updated:", newResolution);
                                      } else {
                                        newSelected.delete(meeting.summary);
                                        setSelectAll(false);
                                        const newResolution = resolutionInput.replace(scheduleString, '');
                                        setResolutionInput(newResolution);
                                        console.log("Resolution input updated:", newResolution);
                                      }
                                      setSelectedEvents(newSelected);
                                    }}
                                    className="h-5 w-5 rounded border-gray-300 text-purple-600 focus:ring-purple-500"
                                  />
                                </div>
                                <div className="mt-2 space-y-1 text-sm text-slate-600">
                                  <p className="flex items-center gap-2">📅 {formatDateTime(meeting.start.dateTime)} - {formatDateTime(meeting.end.dateTime)}</p>
                                  <p className="flex items-center gap-2">📍 {meeting.location || 'No location specified'}</p>
                                  <p className="flex items-center gap-2">👥 {meeting.attendees.map(a => a.email).join(', ')}</p>
                                </div>
                              </div>
                            </div>

                            {/* Conflicting Events Column */}
                            {relatedConflicts && (
                              <div>
                                <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-6">
                                  Conflicting Events ({relatedConflicts.existing_events.length})
                                </h3>
                                <div className="space-y-6">
                                  {relatedConflicts.existing_events.map((existingEvent, eventIndex) => (
                                    <div 
                                      key={eventIndex} 
                                      className="bg-rose-50/80 backdrop-blur-sm rounded-xl p-4 shadow-md border border-rose-100"
                                    >
                                      <h4 className="font-medium text-slate-800 text-xl">
                                        {existingEvent.summary}
                                      </h4>
                                      <div className="mt-2 space-y-1 text-sm text-slate-600">
                                        <p className="flex items-center gap-2">📅 {formatDateTime(existingEvent.start.dateTime)} - {formatDateTime(existingEvent.end.dateTime)}</p>
                                        <p className="flex items-center gap-2">📍 {existingEvent.location || 'No location specified'}</p>
                                        <p className="flex items-center gap-2">👥 {existingEvent.attendees.map(a => a.email).join(', ')}</p>
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                          </div>
                          
                          {/* Resolution Input Section */}
                          <div className="mt-8 px-4 py-4">
                            <div className="flex items-center gap-4 w-full">
                              {relatedConflicts?.existing_events.length > 0 ? (
                                <>
                                  <div className="flex items-center gap-2">
                                    <input
                                      type="checkbox"
                                      checked={replaceConflicting.has(meeting.summary)}
                                      onChange={(e) => {
                                        if (!selectedEvents.has(meeting.summary)) return;
                                        const newReplaceConflicting = new Set(replaceConflicting);
                                        const newMeetingDetails = `
                                          Summary: ${meeting.summary}
                                          Time: ${formatDateTime(meeting.start.dateTime)} - ${formatDateTime(meeting.end.dateTime)}
                                          Location: ${meeting.location || 'No location specified'}
                                          Attendees: ${meeting.attendees.map(a => a.email).join(', ')}
                                        `;

                                        const conflictingEventsDetails = relatedConflicts.existing_events.map(event => `
                                          Summary: ${event.summary}
                                          Time: ${formatDateTime(event.start.dateTime)} - ${formatDateTime(event.end.dateTime)}
                                          Location: ${event.location || 'No location specified'}
                                          Attendees: ${event.attendees.map(a => a.email).join(', ')}
                                        `).join('\n');

                                        const resolutionString = `\n---------------------------------\n\nResolve Conflicting Events for the New meeting:\n${newMeetingDetails}\nBy replacing the conflicting events:\n${conflictingEventsDetails}\nwith the new meeting.\n\n---------------------------------\n`;

                                        if (e.target.checked) {
                                          newReplaceConflicting.add(meeting.summary);
                                          const newResolution = resolutionInput + resolutionString;
                                          setResolutionInput(newResolution);
                                          setDisplayInput(new Map()); // Clear display input
                                          console.log("Resolution input updated:", newResolution);
                                        } else {
                                          newReplaceConflicting.delete(meeting.summary);
                                          // Remove the specific resolution string when unchecked
                                          const newResolution = resolutionInput.replace(resolutionString, '');
                                          setResolutionInput(newResolution);
                                          setDisplayInput(new Map()); // Clear display input
                                          console.log("Resolution input updated:", newResolution);
                                        }
                                        setReplaceConflicting(newReplaceConflicting);
                                      }}
                                      disabled={!selectedEvents.has(meeting.summary)}
                                      className="h-5 w-5 rounded border-gray-300 text-purple-600 focus:ring-purple-500 disabled:opacity-50"
                                    />
                                    <label className="text-sm font-medium text-slate-600">
                                      Replace Conflicting Events
                                    </label>
                                  </div>
                                  <span className="text-slate-400 font-medium">or</span>
                                </>
                              ) : null}
                              <input
                                type="text"
                                value={displayInput.get(meeting.summary) || ''}
                                onChange={(e) => {
                                  if (!selectedEvents.has(meeting.summary) || replaceConflicting.has(meeting.summary)) return;
                                  const newDisplayInput = new Map(displayInput);
                                  newDisplayInput.set(meeting.summary, e.target.value);
                                  setDisplayInput(newDisplayInput);
                                  console.log("Display input updated for", meeting.summary, ":", e.target.value);
                                }}
                                disabled={!selectedEvents.has(meeting.summary) || replaceConflicting.has(meeting.summary)}
                                placeholder={relatedConflicts?.existing_events.length > 0
                                  ? "Enter your custom resolution suggestion to resolve meeting conflicts..."
                                  : "Enter any changes to be made to the event..."}
                                className="flex-1 px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent text-slate-600 disabled:bg-slate-100 disabled:text-slate-400"
                              />
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
                {meetingsData && meetingsData.newMeetings.length > 0 && (
                  <div className="mt-8 flex justify-center">
                    <button
                      onClick={() => {
                        if (selectedEvents.size === 0) {
                          alert('Please select at least one meeting to schedule');
                          return;
                        }
                        
                        let newResolution = resolutionInput;
                        
                        // Add input field content for each selected event
                        meetingsData?.newMeetings.forEach(meeting => {
                          const input = displayInput.get(meeting.summary);
                          if (input?.trim()) {
                            const meetingDetails = `
                              Summary: ${meeting.summary}
                              Time: ${formatDateTime(meeting.start.dateTime)} - ${formatDateTime(meeting.end.dateTime)}
                              Location: ${meeting.location || 'No location specified'}
                              Attendees: ${meeting.attendees.map(a => a.email).join(', ')}
                            `;
                            const inputString = `\n---------------------------------\n\nFor New Meeting:\n${meetingDetails}\n${input}\n---------------------------------\n`;
                            newResolution += inputString;
                          }
                        });
                        
                        // Set the final resolution input in one update
                        setResolutionInput(newResolution);
                        
                        // Clear all display inputs after submission
                        setDisplayInput(new Map());
                        console.log('Final resolution text:', newResolution);
                      }}
                      className="px-8 py-4 bg-gradient-to-r from-blue-500 via-blue-600 to-blue-700 text-white rounded-xl 
                        hover:from-blue-600 hover:via-blue-700 hover:to-blue-800 transition-all duration-300 
                        shadow-lg shadow-blue-500/20 hover:shadow-xl hover:shadow-blue-500/30 hover:-translate-y-0.5
                        font-medium text-lg"
                    >
                      Schedule Meeting{selectedEvents.size !== 1 ? 's' : ''}
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}