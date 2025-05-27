from haystack.dataclasses.image_content import ImageContent
from haystack_experimental.components.builders import ChatPromptBuilder

template = """
{% message role="system" %}
You are a helpful assistant.
{% endmessage %}

{% message role="user" %}
Hello! I am {{user_name}}. What's the difference between the following images?
{% for image in images %}
{{ image | templatize_part }}
{% endfor %}
{% endmessage %}
"""

images = [ImageContent.from_file_path("apple.jpg"), ImageContent.from_file_path("orange.jpg")]

builder = ChatPromptBuilder(template=template)
builder.run(user_name="John", images=images)
