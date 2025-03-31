### USER
In chat completion and regular AI conversations, it’s possible to upload a file and send it. How does that happen in Haystack?  Please use only the haystack documentation at **https://docs.haystack.deepset.ai**

### ASSISTANT
<details type="reasoning" done="true" duration="19">
<summary>Thought for 19 seconds</summary>
> Now I have the detailed information about file uploads in Haystack using Hayhooks.
</details>
In Haystack, file uploads are handled through Hayhooks, which is a web application for serving Haystack pipelines through HTTP endpoints. Here's how file uploads work:

1. **Setup**: First, you need to install Hayhooks using `pip install hayhooks`

2. **File Upload Implementation**: In your pipeline wrapper's `run_api` method, you need to include a parameter for file uploads:
```python
def run_api(self, files: Optional[List[UploadFile]] = None) -> str:
    if files and len(files) > 0:
        filenames = [f.filename for f in files if f.filename is not None]
        file_contents = [f.file.read() for f in files]
        return f"Received files: {', '.join(filenames)}"
    return "No files received"
```

3. **HTTP Request**: The file upload must be sent as a `multipart/form-data` request.

4. **Combined Parameters**: You can handle both files and additional parameters in the same request:
```python
def run_api(self, files: Optional[List[UploadFile]] = None, additional_param: str = "default") -> str:
    # Process both files and parameters
```

5. **CLI Usage**: You can test file uploads from the command line:
```bash
# Upload a single file
hayhooks pipeline run <pipeline_name> --file file.pdf

# Upload multiple files
hayhooks pipeline run <pipeline_name> --file file1.pdf --file file2.pdf

# Upload a directory
hayhooks pipeline run <pipeline_name> --dir files_to_index

# Upload files with additional parameters
hayhooks pipeline run <pipeline_name> --file file.pdf --param 'question="Is this recipe vegan?"'
```

Hayhooks automatically processes the uploaded files and passes them to your pipeline's `run_api` method, making file handling straightforward in Haystack applications.

### USER
How does that interact with chat completion?  That’s not using the run_api method.

### ASSISTANT
<details type="reasoning" done="true" duration="99">
<summary>Thought for 99 seconds</summary>
> Now I have all the information about file uploads with chat completion in Haystack.
</thinking
</details>
For file uploads in Haystack's chat completion functionality, there's an important distinction between the `run_api` and `run_chat_completion` methods in Hayhooks.

While the documentation clearly shows how to handle file uploads with the `run_api` method, it doesn't explicitly demonstrate how to handle file uploads with the `run_chat_completion` method, which is what's used for OpenAI-compatible chat interfaces.

Based on the documentation and GitHub repository, here's how file uploads work with chat completion:

1. **File Upload Implementation**: 
   When implementing the `run_chat_completion` method, you can access file uploads through the `body` parameter, which contains the full request body:

   ```python
   def run_chat_completion(self, model: str, messages: List[dict], body: dict) -> Union[str, Generator]:
       # Access files from the body parameter if present
       # Process the files and include them in your pipeline run
       question = get_last_user_message(messages)
       
       # Use the files in your pipeline
       return self.pipeline.run({"query": question, "files": body.get("files")})
   ```

2. **OpenAI Compatibility**:
   Since Hayhooks creates OpenAI-compatible endpoints, the file upload would follow the OpenAI API format for file attachments. This means files would be included in the request body and accessible through the `body` parameter.

3. **Integration with Chat Interfaces**:
   When using a chat interface like open-webui with Hayhooks as a backend, the file upload functionality would be handled by the chat interface, which would then send the files to the Hayhooks server as part of the OpenAI-compatible request.

4. **Using with OpenAIChatGenerator**:
   When using Hayhooks as a backend for the Haystack OpenAIChatGenerator, you would need to handle file uploads in your pipeline implementation and then access them through the appropriate parameters in your `run_chat_completion` method.

The key difference is that while `run_api` has a standard way to handle file uploads with the `files: Optional[List[UploadFile]] = None` parameter, the `run_chat_completion` method follows the OpenAI API format, where files would be included in the request body and accessible through the `body` parameter.

### USER
How would I bridge that gap?  Can you write some sample code?

### ASSISTANT
<details type="reasoning" done="true" duration="24">
<summary>Thought for 24 seconds</summary>
> I need to write sample code showing how to bridge the gap between file uploads in run_api and run_chat_completion in Hayhooks.
</thinking>
</details>
Here's sample code to bridge the gap between file uploads in `run_api` and `run_chat_completion` in Hayhooks:

```python
from pathlib import Path
from typing import Generator, List, Optional, Union
from fastapi import UploadFile
from haystack import Pipeline
from hayhooks import BasePipelineWrapper, get_last_user_message, streaming_generator

class PipelineWrapper(BasePipelineWrapper):
    def setup(self) -> None:
        # Initialize your pipeline
        pipeline_yaml = (Path(__file__).parent / "my_pipeline.yml").read_text()
        self.pipeline = Pipeline.loads(pipeline_yaml)
    
    # Standard file handling for regular API endpoint
    def run_api(self, files: Optional[List[UploadFile]] = None, query: str = "") -> str:
        """Process files and a query using the pipeline."""
        file_contents = []
        if files and len(files) > 0:
            # Process uploaded files
            file_contents = [
                {"name": f.filename, "content": f.file.read()} 
                for f in files if f.filename is not None
            ]
        
        # Run pipeline with files and query
        result = self.pipeline.run({
            "query": query,
            "files": file_contents
        })
        
        return result["output"]["text"]
    
    # Bridge to handle files in chat completion
    def run_chat_completion(self, model: str, messages: List[dict], body: dict) -> Union[str, Generator]:
        """
        OpenAI-compatible chat completion that handles file uploads.
        
        The body parameter contains the full request, including any file attachments.
        """
        # Extract the query from the last user message
        query = get_last_user_message(messages)
        
        # Check if we have files in the request body
        file_contents = []
        if "files" in body and body["files"]:
            # Process files from the OpenAI-compatible request
            # Note: The exact format may depend on how the client sends files
            for file_data in body["files"]:
                file_contents.append({
                    "name": file_data.get("filename"),
                    "content": file_data.get("content")
                })
        
        # For streaming response
        if body.get("stream", False):
            return streaming_generator(
                pipeline=self.pipeline,
                pipeline_run_args={
                    "query": query,
                    "files": file_contents
                }
            )
        
        # For non-streaming response
        result = self.pipeline.run({
            "query": query,
            "files": file_contents
        })
        
        return result["output"]["text"]
```

Since OpenAI's API doesn't have a standardized way to handle file uploads in chat completions, you might need to create a custom endpoint to handle this specific use case. Here's how you could extend your Hayhooks implementation:

```python
# In a custom app.py file
import uvicorn
from typing import List
from fastapi import FastAPI, File, Form, UploadFile
from hayhooks import create_app
from hayhooks.settings import settings

# Create the Hayhooks app
hayhooks = create_app()

# Add a custom endpoint for file uploads with chat
@hayhooks.post("/{pipeline_name}/chat_with_files")
async def chat_with_files(
    pipeline_name: str,
    files: List[UploadFile] = File(...),
    messages: str = Form(...),  # JSON string of messages
    model: str = Form(None),
    temperature: float = Form(0.7),
    max_tokens: int = Form(None),
):
    """Custom endpoint that combines file uploads with chat completion."""
    import json
    from hayhooks.registry import get_pipeline_wrapper
    
    # Get the pipeline wrapper
    wrapper = get_pipeline_wrapper(pipeline_name)
    if not wrapper:
        return {"error": f"Pipeline {pipeline_name} not found"}
    
    # Parse messages from JSON string
    try:
        messages_list = json.loads(messages)
    except json.JSONDecodeError:
        return {"error": "Invalid messages format"}
    
    # Create a body that includes both files and chat parameters
    body = {
        "model": model or pipeline_name,
        "messages": messages_list,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "files": files
    }
    
    # Call the run_chat_completion method with our custom body
    response = wrapper.run_chat_completion(
        model=body["model"],
        messages=body["messages"],
        body=body
    )
    
    return {"content": response}

if __name__ == "__main__":
    uvicorn.run("app:hayhooks", host=settings.host, port=settings.port)
```

To use this in a client application:

```python
import json
import requests

# URL of your Hayhooks server with the custom endpoint
url = "http://localhost:1416/my_pipeline/chat_with_files"

# Prepare the files and messages
files = [
    ('files', ('document.pdf', open('document.pdf', 'rb'), 'application/pdf'))
]

# Prepare chat messages
messages = [
    {"role": "user", "content": "Summarize the contents of this PDF file"}
]

# Send the request
response = requests.post(
    url,
    files=files,
    data={
        "messages": json.dumps(messages),
        "model": "my_pipeline",
        "temperature": 0.7
    }
)

print(response.json())
```

This approach creates a custom endpoint that accepts both file uploads and chat messages, bridging the gap between the standard file upload mechanism and the OpenAI-compatible chat completion interface.