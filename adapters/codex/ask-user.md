When a material decision or clarification is needed, use `request_user_input`
if it is available in the current session and mode. Follow its current schema,
including stable question IDs, short headers, and meaningful options.
Use the returned answer, including free text, to guide the next step.
If the tool is unavailable, ask the question in chat and wait for the answer.
Do not interpret silence or a tool timeout as permission for a consequential action.
