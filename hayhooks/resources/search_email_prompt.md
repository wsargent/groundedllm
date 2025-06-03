You will be provided with a list of email messages. Your task is to:
1. Identify emails that are relevant to the user's query.
2. For each relevant email, create a concise summary that includes the sections of the mail relevant to the user's query.
3. Return the list of email summaries to the user in Markdown format.

User's query: {{query}}

Email messages:
{% for doc in documents %}
  --- Email Start ---
  Subject: {{ doc.meta.subject }}
  From: {{ doc.meta.sender }}
  Date: {{ doc.meta.date }}
  Snippet: {{ doc.meta.snippet }}
  Content: {{ doc.content }}
  --- Email End ---
{% endfor %}

If no emails are relevant, return a message like "No relevant emails found." or an empty response.
Focus on extracting key information related to the query.