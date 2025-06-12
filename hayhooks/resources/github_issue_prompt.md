{% for document in documents %}
{% if document.meta.type == 'issue' %}
"**Issue Title:** {{ document.meta.title }}
"**Issue Description:** {{ document.content }}
{% else %}
**Comment by {{ document.meta.author }}:** {{ document.content }}
{% endif %}
{% endfor %}