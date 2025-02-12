NoteTaker is the keeper of notes for a user. 

NoteTaker interacts with a user who supplies blocks of knowledge as text, who asks questions, and who can be asked questions. 

Models the user's planned actions can be revised, abandoned, etc. at each step.  There may be many available actions , so the agent needs to prioritize at each step.  

NoteTaker, when processing input text, considers the text, the current state of Notes, and the user's immediate and high-level goals to form plans for what information it needs, what questions it should ask of the user. 

Specific use case: Track of people, projects, events, and plans in my professional life. The workflow would be that I paste in information to be analyzed and represented in the Notes and also answer questions from NoteTaker to interactively clarify and expand on what I provide. I can also ask questions to NoteTaker. NoteTaker's Notes are regularly backed up to NDEx and can persist indefinitely.  

(4) revise notes, (5) respond to a user query, and possibly (6) explicitly ask itself to think about something, i.e. adopt a mode of thought to accomplish a planned action.  Multiple actions can be proposed at a given time, linked with dependencies, forming plans. 

Information gathering actions such as web search, but simply making plans for what it needs to know - and notes on what it has already asked and been told - is already complicated.  It should remember what it has asked before because the history is present as Flow objects representing each iteration, linked with next and previous links.   To compose the prompt for an iteration, we choose a window of prior iterations (full thinking and transactions for each iteration), plus the current planned actions, and...To Be Designed,.:-)s