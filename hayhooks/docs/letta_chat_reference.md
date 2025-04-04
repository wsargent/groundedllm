# Reference
## Tools
<details><summary><code>client.tools.<a href="src/letta_client/tools/client.py">retrieve</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Get a tool by ID
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.tools.retrieve(
    tool_id="tool_id",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**tool_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.tools.<a href="src/letta_client/tools/client.py">delete</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Delete a tool by name
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.tools.delete(
    tool_id="tool_id",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**tool_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.tools.<a href="src/letta_client/tools/client.py">modify</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Update an existing tool
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.tools.modify(
    tool_id="tool_id",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**tool_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**description:** `typing.Optional[str]` — The description of the tool.
    
</dd>
</dl>

<dl>
<dd>

**tags:** `typing.Optional[typing.Sequence[str]]` — Metadata tags.
    
</dd>
</dl>

<dl>
<dd>

**source_code:** `typing.Optional[str]` — The source code of the function.
    
</dd>
</dl>

<dl>
<dd>

**source_type:** `typing.Optional[str]` — The type of the source code.
    
</dd>
</dl>

<dl>
<dd>

**json_schema:** `typing.Optional[typing.Dict[str, typing.Optional[typing.Any]]]` — The JSON schema of the function (auto-generated from source_code if not provided)
    
</dd>
</dl>

<dl>
<dd>

**args_json_schema:** `typing.Optional[typing.Dict[str, typing.Optional[typing.Any]]]` — The args JSON schema of the function.
    
</dd>
</dl>

<dl>
<dd>

**return_char_limit:** `typing.Optional[int]` — The maximum number of characters in the response.
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.tools.<a href="src/letta_client/tools/client.py">list</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Get a list of all tools available to agents belonging to the org of the user
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.tools.list()

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**after:** `typing.Optional[str]` 
    
</dd>
</dl>

<dl>
<dd>

**limit:** `typing.Optional[int]` 
    
</dd>
</dl>

<dl>
<dd>

**name:** `typing.Optional[str]` 
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.tools.<a href="src/letta_client/tools/client.py">create</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Create a new tool
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.tools.create(
    source_code="source_code",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**source_code:** `str` — The source code of the function.
    
</dd>
</dl>

<dl>
<dd>

**description:** `typing.Optional[str]` — The description of the tool.
    
</dd>
</dl>

<dl>
<dd>

**tags:** `typing.Optional[typing.Sequence[str]]` — Metadata tags.
    
</dd>
</dl>

<dl>
<dd>

**source_type:** `typing.Optional[str]` — The source type of the function.
    
</dd>
</dl>

<dl>
<dd>

**json_schema:** `typing.Optional[typing.Dict[str, typing.Optional[typing.Any]]]` — The JSON schema of the function (auto-generated from source_code if not provided)
    
</dd>
</dl>

<dl>
<dd>

**args_json_schema:** `typing.Optional[typing.Dict[str, typing.Optional[typing.Any]]]` — The args JSON schema of the function.
    
</dd>
</dl>

<dl>
<dd>

**return_char_limit:** `typing.Optional[int]` — The maximum number of characters in the response.
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.tools.<a href="src/letta_client/tools/client.py">upsert</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Create or update a tool
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.tools.upsert(
    source_code="source_code",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**source_code:** `str` — The source code of the function.
    
</dd>
</dl>

<dl>
<dd>

**description:** `typing.Optional[str]` — The description of the tool.
    
</dd>
</dl>

<dl>
<dd>

**tags:** `typing.Optional[typing.Sequence[str]]` — Metadata tags.
    
</dd>
</dl>

<dl>
<dd>

**source_type:** `typing.Optional[str]` — The source type of the function.
    
</dd>
</dl>

<dl>
<dd>

**json_schema:** `typing.Optional[typing.Dict[str, typing.Optional[typing.Any]]]` — The JSON schema of the function (auto-generated from source_code if not provided)
    
</dd>
</dl>

<dl>
<dd>

**args_json_schema:** `typing.Optional[typing.Dict[str, typing.Optional[typing.Any]]]` — The args JSON schema of the function.
    
</dd>
</dl>

<dl>
<dd>

**return_char_limit:** `typing.Optional[int]` — The maximum number of characters in the response.
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.tools.<a href="src/letta_client/tools/client.py">add_base_tool</a>()</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Upsert base tools
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.tools.add_base_tool()

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.tools.<a href="src/letta_client/tools/client.py">run_tool_from_source</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Attempt to build a tool from source, then run it on the provided arguments
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.tools.run_tool_from_source(
    source_code="source_code",
    args={"key": "value"},
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**source_code:** `str` — The source code of the function.
    
</dd>
</dl>

<dl>
<dd>

**args:** `typing.Dict[str, typing.Optional[typing.Any]]` — The arguments to pass to the tool.
    
</dd>
</dl>

<dl>
<dd>

**env_vars:** `typing.Optional[typing.Dict[str, str]]` — The environment variables to pass to the tool.
    
</dd>
</dl>

<dl>
<dd>

**name:** `typing.Optional[str]` — The name of the tool to run.
    
</dd>
</dl>

<dl>
<dd>

**source_type:** `typing.Optional[str]` — The type of the source code.
    
</dd>
</dl>

<dl>
<dd>

**args_json_schema:** `typing.Optional[typing.Dict[str, typing.Optional[typing.Any]]]` — The args JSON schema of the function.
    
</dd>
</dl>

<dl>
<dd>

**json_schema:** `typing.Optional[typing.Dict[str, typing.Optional[typing.Any]]]` — The JSON schema of the function (auto-generated from source_code if not provided)
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.tools.<a href="src/letta_client/tools/client.py">list_composio_apps</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Get a list of all Composio apps
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.tools.list_composio_apps()

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**user_id:** `typing.Optional[str]` 
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.tools.<a href="src/letta_client/tools/client.py">list_composio_actions_by_app</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Get a list of all Composio actions for a specific app
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.tools.list_composio_actions_by_app(
    composio_app_name="composio_app_name",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**composio_app_name:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.tools.<a href="src/letta_client/tools/client.py">add_composio_tool</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Add a new Composio tool by action name (Composio refers to each tool as an `Action`)
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.tools.add_composio_tool(
    composio_action_name="composio_action_name",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**composio_action_name:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.tools.<a href="src/letta_client/tools/client.py">list_mcp_servers</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Get a list of all configured MCP servers
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.tools.list_mcp_servers()

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**user_id:** `typing.Optional[str]` 
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.tools.<a href="src/letta_client/tools/client.py">add_mcp_server</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Add a new MCP server to the Letta MCP server config
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta, StdioServerConfig

client = Letta(
    token="YOUR_TOKEN",
)
client.tools.add_mcp_server(
    request=StdioServerConfig(
        server_name="server_name",
        command="command",
        args=["args"],
    ),
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**request:** `AddMcpServerRequest` 
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.tools.<a href="src/letta_client/tools/client.py">list_mcp_tools_by_server</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Get a list of all tools for a specific MCP server
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.tools.list_mcp_tools_by_server(
    mcp_server_name="mcp_server_name",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**mcp_server_name:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.tools.<a href="src/letta_client/tools/client.py">add_mcp_tool</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Register a new MCP tool as a Letta server by MCP server + tool name
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.tools.add_mcp_tool(
    mcp_server_name="mcp_server_name",
    mcp_tool_name="mcp_tool_name",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**mcp_server_name:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**mcp_tool_name:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.tools.<a href="src/letta_client/tools/client.py">delete_mcp_server</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Add a new MCP server to the Letta MCP server config
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.tools.delete_mcp_server(
    mcp_server_name="mcp_server_name",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**mcp_server_name:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

## Sources
<details><summary><code>client.sources.<a href="src/letta_client/sources/client.py">retrieve</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Get all sources
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.sources.retrieve(
    source_id="source_id",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**source_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.sources.<a href="src/letta_client/sources/client.py">delete</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Delete a data source.
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.sources.delete(
    source_id="source_id",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**source_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.sources.<a href="src/letta_client/sources/client.py">modify</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Update the name or documentation of an existing data source.
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.sources.modify(
    source_id="source_id",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**source_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**name:** `typing.Optional[str]` — The name of the source.
    
</dd>
</dl>

<dl>
<dd>

**description:** `typing.Optional[str]` — The description of the source.
    
</dd>
</dl>

<dl>
<dd>

**metadata:** `typing.Optional[typing.Dict[str, typing.Optional[typing.Any]]]` — Metadata associated with the source.
    
</dd>
</dl>

<dl>
<dd>

**embedding_config:** `typing.Optional[EmbeddingConfig]` — The embedding configuration used by the source.
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.sources.<a href="src/letta_client/sources/client.py">get_by_name</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Get a source by name
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.sources.get_by_name(
    source_name="source_name",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**source_name:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.sources.<a href="src/letta_client/sources/client.py">list</a>()</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

List all data sources created by a user.
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.sources.list()

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.sources.<a href="src/letta_client/sources/client.py">create</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Create a new data source.
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.sources.create(
    name="name",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**name:** `str` — The name of the source.
    
</dd>
</dl>

<dl>
<dd>

**embedding:** `typing.Optional[str]` — The hande for the embedding config used by the source.
    
</dd>
</dl>

<dl>
<dd>

**embedding_chunk_size:** `typing.Optional[int]` — The chunk size of the embedding.
    
</dd>
</dl>

<dl>
<dd>

**embedding_config:** `typing.Optional[EmbeddingConfig]` — (Legacy) The embedding configuration used by the source.
    
</dd>
</dl>

<dl>
<dd>

**description:** `typing.Optional[str]` — The description of the source.
    
</dd>
</dl>

<dl>
<dd>

**metadata:** `typing.Optional[typing.Dict[str, typing.Optional[typing.Any]]]` — Metadata associated with the source.
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

## Agents
<details><summary><code>client.agents.<a href="src/letta_client/agents/client.py">list</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

List all agents associated with a given user.

This endpoint retrieves a list of all agents and their configurations
associated with the specified user ID.
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.agents.list()

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**name:** `typing.Optional[str]` — Name of the agent
    
</dd>
</dl>

<dl>
<dd>

**tags:** `typing.Optional[typing.Union[str, typing.Sequence[str]]]` — List of tags to filter agents by
    
</dd>
</dl>

<dl>
<dd>

**match_all_tags:** `typing.Optional[bool]` — If True, only returns agents that match ALL given tags. Otherwise, return agents that have ANY of the passed-in tags.
    
</dd>
</dl>

<dl>
<dd>

**before:** `typing.Optional[str]` — Cursor for pagination
    
</dd>
</dl>

<dl>
<dd>

**after:** `typing.Optional[str]` — Cursor for pagination
    
</dd>
</dl>

<dl>
<dd>

**limit:** `typing.Optional[int]` — Limit for pagination
    
</dd>
</dl>

<dl>
<dd>

**query_text:** `typing.Optional[str]` — Search agents by name
    
</dd>
</dl>

<dl>
<dd>

**project_id:** `typing.Optional[str]` — Search agents by project ID
    
</dd>
</dl>

<dl>
<dd>

**template_id:** `typing.Optional[str]` — Search agents by template ID
    
</dd>
</dl>

<dl>
<dd>

**base_template_id:** `typing.Optional[str]` — Search agents by base template ID
    
</dd>
</dl>

<dl>
<dd>

**identity_id:** `typing.Optional[str]` — Search agents by identity ID
    
</dd>
</dl>

<dl>
<dd>

**identifier_keys:** `typing.Optional[typing.Union[str, typing.Sequence[str]]]` — Search agents by identifier keys
    
</dd>
</dl>

<dl>
<dd>

**include_relationships:** `typing.Optional[typing.Union[str, typing.Sequence[str]]]` — Specify which relational fields (e.g., 'tools', 'sources', 'memory') to include in the response. If not provided, all relationships are loaded by default. Using this can optimize performance by reducing unnecessary joins.
    
</dd>
</dl>

<dl>
<dd>

**ascending:** `typing.Optional[bool]` — Whether to sort agents oldest to newest (True) or newest to oldest (False, default)
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.agents.<a href="src/letta_client/agents/client.py">create</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Create a new agent with the specified configuration.
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.agents.create()

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**project:** `typing.Optional[str]` 
    
</dd>
</dl>

<dl>
<dd>

**name:** `typing.Optional[str]` — The name of the agent.
    
</dd>
</dl>

<dl>
<dd>

**memory_blocks:** `typing.Optional[typing.Sequence[CreateBlock]]` — The blocks to create in the agent's in-context memory.
    
</dd>
</dl>

<dl>
<dd>

**tools:** `typing.Optional[typing.Sequence[str]]` — The tools used by the agent.
    
</dd>
</dl>

<dl>
<dd>

**tool_ids:** `typing.Optional[typing.Sequence[str]]` — The ids of the tools used by the agent.
    
</dd>
</dl>

<dl>
<dd>

**source_ids:** `typing.Optional[typing.Sequence[str]]` — The ids of the sources used by the agent.
    
</dd>
</dl>

<dl>
<dd>

**block_ids:** `typing.Optional[typing.Sequence[str]]` — The ids of the blocks used by the agent.
    
</dd>
</dl>

<dl>
<dd>

**tool_rules:** `typing.Optional[typing.Sequence[CreateAgentRequestToolRulesItem]]` — The tool rules governing the agent.
    
</dd>
</dl>

<dl>
<dd>

**tags:** `typing.Optional[typing.Sequence[str]]` — The tags associated with the agent.
    
</dd>
</dl>

<dl>
<dd>

**system:** `typing.Optional[str]` — The system prompt used by the agent.
    
</dd>
</dl>

<dl>
<dd>

**agent_type:** `typing.Optional[AgentType]` — The type of agent.
    
</dd>
</dl>

<dl>
<dd>

**llm_config:** `typing.Optional[LlmConfig]` — The LLM configuration used by the agent.
    
</dd>
</dl>

<dl>
<dd>

**embedding_config:** `typing.Optional[EmbeddingConfig]` — The embedding configuration used by the agent.
    
</dd>
</dl>

<dl>
<dd>

**initial_message_sequence:** `typing.Optional[typing.Sequence[MessageCreate]]` — The initial set of messages to put in the agent's in-context memory.
    
</dd>
</dl>

<dl>
<dd>

**include_base_tools:** `typing.Optional[bool]` — If true, attaches the Letta core tools (e.g. archival_memory and core_memory related functions).
    
</dd>
</dl>

<dl>
<dd>

**include_multi_agent_tools:** `typing.Optional[bool]` — If true, attaches the Letta multi-agent tools (e.g. sending a message to another agent).
    
</dd>
</dl>

<dl>
<dd>

**include_base_tool_rules:** `typing.Optional[bool]` — If true, attaches the Letta base tool rules (e.g. deny all tools not explicitly allowed).
    
</dd>
</dl>

<dl>
<dd>

**description:** `typing.Optional[str]` — The description of the agent.
    
</dd>
</dl>

<dl>
<dd>

**metadata:** `typing.Optional[typing.Dict[str, typing.Optional[typing.Any]]]` — The metadata of the agent.
    
</dd>
</dl>

<dl>
<dd>

**model:** `typing.Optional[str]` — The LLM configuration handle used by the agent, specified in the format provider/model-name, as an alternative to specifying llm_config.
    
</dd>
</dl>

<dl>
<dd>

**embedding:** `typing.Optional[str]` — The embedding configuration handle used by the agent, specified in the format provider/model-name.
    
</dd>
</dl>

<dl>
<dd>

**context_window_limit:** `typing.Optional[int]` — The context window limit used by the agent.
    
</dd>
</dl>

<dl>
<dd>

**embedding_chunk_size:** `typing.Optional[int]` — The embedding chunk size used by the agent.
    
</dd>
</dl>

<dl>
<dd>

**max_tokens:** `typing.Optional[int]` — The maximum number of tokens to generate, including reasoning step. If not set, the model will use its default value.
    
</dd>
</dl>

<dl>
<dd>

**max_reasoning_tokens:** `typing.Optional[int]` — The maximum number of tokens to generate for reasoning step. If not set, the model will use its default value.
    
</dd>
</dl>

<dl>
<dd>

**enable_reasoner:** `typing.Optional[bool]` — Whether to enable internal extended thinking step for a reasoner model.
    
</dd>
</dl>

<dl>
<dd>

**from_template:** `typing.Optional[str]` — The template id used to configure the agent
    
</dd>
</dl>

<dl>
<dd>

**template:** `typing.Optional[bool]` — Whether the agent is a template
    
</dd>
</dl>

<dl>
<dd>

**create_agent_request_project:** `typing.Optional[str]` — Deprecated: Project should now be passed via the X-Project header instead of in the request body. If using the sdk, this can be done via the new x_project field below.
    
</dd>
</dl>

<dl>
<dd>

**tool_exec_environment_variables:** `typing.Optional[typing.Dict[str, typing.Optional[str]]]` — The environment variables for tool execution specific to this agent.
    
</dd>
</dl>

<dl>
<dd>

**memory_variables:** `typing.Optional[typing.Dict[str, typing.Optional[str]]]` — The variables that should be set for the agent.
    
</dd>
</dl>

<dl>
<dd>

**project_id:** `typing.Optional[str]` — The id of the project the agent belongs to.
    
</dd>
</dl>

<dl>
<dd>

**template_id:** `typing.Optional[str]` — The id of the template the agent belongs to.
    
</dd>
</dl>

<dl>
<dd>

**base_template_id:** `typing.Optional[str]` — The base template id of the agent.
    
</dd>
</dl>

<dl>
<dd>

**identity_ids:** `typing.Optional[typing.Sequence[str]]` — The ids of the identities associated with this agent.
    
</dd>
</dl>

<dl>
<dd>

**message_buffer_autoclear:** `typing.Optional[bool]` — If set to True, the agent will not remember previous messages (though the agent will still retain state via core memory blocks and archival/recall memory). Not recommended unless you have an advanced use case.
    
</dd>
</dl>

<dl>
<dd>

**enable_sleeptime:** `typing.Optional[bool]` — If set to True, memory management will move to a background agent thread.
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.agents.<a href="src/letta_client/agents/client.py">export_agent_serialized</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Export the serialized JSON representation of an agent.
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.agents.export_agent_serialized(
    agent_id="agent_id",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**agent_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.agents.<a href="src/letta_client/agents/client.py">import_agent_serialized</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Import a serialized agent file and recreate the agent in the system.
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.agents.import_agent_serialized()

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**file:** `from __future__ import annotations

core.File` — See core.File for more documentation
    
</dd>
</dl>

<dl>
<dd>

**append_copy_suffix:** `typing.Optional[bool]` — If set to True, appends "_copy" to the end of the agent name.
    
</dd>
</dl>

<dl>
<dd>

**override_existing_tools:** `typing.Optional[bool]` — If set to True, existing tools can get their source code overwritten by the uploaded tool definitions. Note that Letta core tools can never be updated externally.
    
</dd>
</dl>

<dl>
<dd>

**project_id:** `typing.Optional[str]` — The project ID to associate the uploaded agent with.
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.agents.<a href="src/letta_client/agents/client.py">retrieve</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Get the state of the agent.
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.agents.retrieve(
    agent_id="agent_id",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**agent_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.agents.<a href="src/letta_client/agents/client.py">delete</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Delete an agent.
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.agents.delete(
    agent_id="agent_id",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**agent_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.agents.<a href="src/letta_client/agents/client.py">modify</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Update an existing agent
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.agents.modify(
    agent_id="agent_id",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**agent_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**name:** `typing.Optional[str]` — The name of the agent.
    
</dd>
</dl>

<dl>
<dd>

**tool_ids:** `typing.Optional[typing.Sequence[str]]` — The ids of the tools used by the agent.
    
</dd>
</dl>

<dl>
<dd>

**source_ids:** `typing.Optional[typing.Sequence[str]]` — The ids of the sources used by the agent.
    
</dd>
</dl>

<dl>
<dd>

**block_ids:** `typing.Optional[typing.Sequence[str]]` — The ids of the blocks used by the agent.
    
</dd>
</dl>

<dl>
<dd>

**tags:** `typing.Optional[typing.Sequence[str]]` — The tags associated with the agent.
    
</dd>
</dl>

<dl>
<dd>

**system:** `typing.Optional[str]` — The system prompt used by the agent.
    
</dd>
</dl>

<dl>
<dd>

**tool_rules:** `typing.Optional[typing.Sequence[UpdateAgentToolRulesItem]]` — The tool rules governing the agent.
    
</dd>
</dl>

<dl>
<dd>

**llm_config:** `typing.Optional[LlmConfig]` — The LLM configuration used by the agent.
    
</dd>
</dl>

<dl>
<dd>

**embedding_config:** `typing.Optional[EmbeddingConfig]` — The embedding configuration used by the agent.
    
</dd>
</dl>

<dl>
<dd>

**message_ids:** `typing.Optional[typing.Sequence[str]]` — The ids of the messages in the agent's in-context memory.
    
</dd>
</dl>

<dl>
<dd>

**description:** `typing.Optional[str]` — The description of the agent.
    
</dd>
</dl>

<dl>
<dd>

**metadata:** `typing.Optional[typing.Dict[str, typing.Optional[typing.Any]]]` — The metadata of the agent.
    
</dd>
</dl>

<dl>
<dd>

**tool_exec_environment_variables:** `typing.Optional[typing.Dict[str, typing.Optional[str]]]` — The environment variables for tool execution specific to this agent.
    
</dd>
</dl>

<dl>
<dd>

**project_id:** `typing.Optional[str]` — The id of the project the agent belongs to.
    
</dd>
</dl>

<dl>
<dd>

**template_id:** `typing.Optional[str]` — The id of the template the agent belongs to.
    
</dd>
</dl>

<dl>
<dd>

**base_template_id:** `typing.Optional[str]` — The base template id of the agent.
    
</dd>
</dl>

<dl>
<dd>

**identity_ids:** `typing.Optional[typing.Sequence[str]]` — The ids of the identities associated with this agent.
    
</dd>
</dl>

<dl>
<dd>

**message_buffer_autoclear:** `typing.Optional[bool]` — If set to True, the agent will not remember previous messages (though the agent will still retain state via core memory blocks and archival/recall memory). Not recommended unless you have an advanced use case.
    
</dd>
</dl>

<dl>
<dd>

**model:** `typing.Optional[str]` — The LLM configuration handle used by the agent, specified in the format provider/model-name, as an alternative to specifying llm_config.
    
</dd>
</dl>

<dl>
<dd>

**embedding:** `typing.Optional[str]` — The embedding configuration handle used by the agent, specified in the format provider/model-name.
    
</dd>
</dl>

<dl>
<dd>

**enable_sleeptime:** `typing.Optional[bool]` — If set to True, memory management will move to a background agent thread.
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.agents.<a href="src/letta_client/agents/client.py">modify_passage</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Modify a memory in the agent's archival memory store.
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.agents.modify_passage(
    agent_id="agent_id",
    memory_id="memory_id",
    id="id",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**agent_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**memory_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**id:** `str` — The unique identifier of the passage.
    
</dd>
</dl>

<dl>
<dd>

**created_by_id:** `typing.Optional[str]` — The id of the user that made this object.
    
</dd>
</dl>

<dl>
<dd>

**last_updated_by_id:** `typing.Optional[str]` — The id of the user that made this object.
    
</dd>
</dl>

<dl>
<dd>

**created_at:** `typing.Optional[dt.datetime]` — The timestamp when the object was created.
    
</dd>
</dl>

<dl>
<dd>

**updated_at:** `typing.Optional[dt.datetime]` — The timestamp when the object was last updated.
    
</dd>
</dl>

<dl>
<dd>

**is_deleted:** `typing.Optional[bool]` — Whether this passage is deleted or not.
    
</dd>
</dl>

<dl>
<dd>

**passage_update_agent_id:** `typing.Optional[str]` — The unique identifier of the agent associated with the passage.
    
</dd>
</dl>

<dl>
<dd>

**source_id:** `typing.Optional[str]` — The data source of the passage.
    
</dd>
</dl>

<dl>
<dd>

**file_id:** `typing.Optional[str]` — The unique identifier of the file associated with the passage.
    
</dd>
</dl>

<dl>
<dd>

**metadata:** `typing.Optional[typing.Dict[str, typing.Optional[typing.Any]]]` — The metadata of the passage.
    
</dd>
</dl>

<dl>
<dd>

**text:** `typing.Optional[str]` — The text of the passage.
    
</dd>
</dl>

<dl>
<dd>

**embedding:** `typing.Optional[typing.Sequence[float]]` — The embedding of the passage.
    
</dd>
</dl>

<dl>
<dd>

**embedding_config:** `typing.Optional[EmbeddingConfig]` — The embedding configuration used by the passage.
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.agents.<a href="src/letta_client/agents/client.py">reset_messages</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Resets the messages for an agent
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.agents.reset_messages(
    agent_id="agent_id",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**agent_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**add_default_initial_messages:** `typing.Optional[bool]` — If true, adds the default initial messages after resetting.
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.agents.<a href="src/letta_client/agents/client.py">search</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

<Note>This endpoint is only available on Letta Cloud.</Note>

Search deployed agents.
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.agents.search()

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**search:** `typing.Optional[typing.Sequence[AgentsSearchRequestSearchItem]]` 
    
</dd>
</dl>

<dl>
<dd>

**project_id:** `typing.Optional[str]` 
    
</dd>
</dl>

<dl>
<dd>

**combinator:** `typing.Optional[typing.Literal["AND"]]` 
    
</dd>
</dl>

<dl>
<dd>

**limit:** `typing.Optional[float]` 
    
</dd>
</dl>

<dl>
<dd>

**after:** `typing.Optional[str]` 
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

## Groups
<details><summary><code>client.groups.<a href="src/letta_client/groups/client.py">list</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Fetch all multi-agent groups matching query.
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.groups.list()

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**manager_type:** `typing.Optional[ManagerType]` — Search groups by manager type
    
</dd>
</dl>

<dl>
<dd>

**before:** `typing.Optional[str]` — Cursor for pagination
    
</dd>
</dl>

<dl>
<dd>

**after:** `typing.Optional[str]` — Cursor for pagination
    
</dd>
</dl>

<dl>
<dd>

**limit:** `typing.Optional[int]` — Limit for pagination
    
</dd>
</dl>

<dl>
<dd>

**project_id:** `typing.Optional[str]` — Search groups by project id
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.groups.<a href="src/letta_client/groups/client.py">create</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Create a new multi-agent group with the specified configuration.
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.groups.create(
    agent_ids=["agent_ids"],
    description="description",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**agent_ids:** `typing.Sequence[str]` — 
    
</dd>
</dl>

<dl>
<dd>

**description:** `str` — 
    
</dd>
</dl>

<dl>
<dd>

**project:** `typing.Optional[str]` 
    
</dd>
</dl>

<dl>
<dd>

**manager_config:** `typing.Optional[GroupCreateManagerConfig]` — 
    
</dd>
</dl>

<dl>
<dd>

**shared_block_ids:** `typing.Optional[typing.Sequence[str]]` — 
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.groups.<a href="src/letta_client/groups/client.py">retrieve</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Retrieve the group by id.
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.groups.retrieve(
    group_id="group_id",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**group_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.groups.<a href="src/letta_client/groups/client.py">modify_group</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Create a new multi-agent group with the specified configuration.
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.groups.modify_group(
    group_id="group_id",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**group_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**project:** `typing.Optional[str]` 
    
</dd>
</dl>

<dl>
<dd>

**agent_ids:** `typing.Optional[typing.Sequence[str]]` — 
    
</dd>
</dl>

<dl>
<dd>

**description:** `typing.Optional[str]` — 
    
</dd>
</dl>

<dl>
<dd>

**manager_config:** `typing.Optional[GroupUpdateManagerConfig]` — 
    
</dd>
</dl>

<dl>
<dd>

**shared_block_ids:** `typing.Optional[typing.Sequence[str]]` — 
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.groups.<a href="src/letta_client/groups/client.py">delete</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Delete a multi-agent group.
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.groups.delete(
    group_id="group_id",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**group_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.groups.<a href="src/letta_client/groups/client.py">modify</a>(...)</code></summary>
<dl>
<dd>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.groups.modify(
    group_id="group_id",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**group_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.groups.<a href="src/letta_client/groups/client.py">reset_messages</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Delete the group messages for all agents that are part of the multi-agent group.
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.groups.reset_messages(
    group_id="group_id",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**group_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

## Identities
<details><summary><code>client.identities.<a href="src/letta_client/identities/client.py">list</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Get a list of all identities in the database
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.identities.list()

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**name:** `typing.Optional[str]` 
    
</dd>
</dl>

<dl>
<dd>

**project_id:** `typing.Optional[str]` 
    
</dd>
</dl>

<dl>
<dd>

**identifier_key:** `typing.Optional[str]` 
    
</dd>
</dl>

<dl>
<dd>

**identity_type:** `typing.Optional[IdentityType]` 
    
</dd>
</dl>

<dl>
<dd>

**before:** `typing.Optional[str]` 
    
</dd>
</dl>

<dl>
<dd>

**after:** `typing.Optional[str]` 
    
</dd>
</dl>

<dl>
<dd>

**limit:** `typing.Optional[int]` 
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.identities.<a href="src/letta_client/identities/client.py">create</a>(...)</code></summary>
<dl>
<dd>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.identities.create(
    identifier_key="identifier_key",
    name="name",
    identity_type="org",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**identifier_key:** `str` — External, user-generated identifier key of the identity.
    
</dd>
</dl>

<dl>
<dd>

**name:** `str` — The name of the identity.
    
</dd>
</dl>

<dl>
<dd>

**identity_type:** `IdentityType` — The type of the identity.
    
</dd>
</dl>

<dl>
<dd>

**project:** `typing.Optional[str]` 
    
</dd>
</dl>

<dl>
<dd>

**project_id:** `typing.Optional[str]` — The project id of the identity, if applicable.
    
</dd>
</dl>

<dl>
<dd>

**agent_ids:** `typing.Optional[typing.Sequence[str]]` — The agent ids that are associated with the identity.
    
</dd>
</dl>

<dl>
<dd>

**block_ids:** `typing.Optional[typing.Sequence[str]]` — The IDs of the blocks associated with the identity.
    
</dd>
</dl>

<dl>
<dd>

**properties:** `typing.Optional[typing.Sequence[IdentityProperty]]` — List of properties associated with the identity.
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.identities.<a href="src/letta_client/identities/client.py">upsert</a>(...)</code></summary>
<dl>
<dd>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.identities.upsert(
    identifier_key="identifier_key",
    name="name",
    identity_type="org",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**identifier_key:** `str` — External, user-generated identifier key of the identity.
    
</dd>
</dl>

<dl>
<dd>

**name:** `str` — The name of the identity.
    
</dd>
</dl>

<dl>
<dd>

**identity_type:** `IdentityType` — The type of the identity.
    
</dd>
</dl>

<dl>
<dd>

**project:** `typing.Optional[str]` 
    
</dd>
</dl>

<dl>
<dd>

**project_id:** `typing.Optional[str]` — The project id of the identity, if applicable.
    
</dd>
</dl>

<dl>
<dd>

**agent_ids:** `typing.Optional[typing.Sequence[str]]` — The agent ids that are associated with the identity.
    
</dd>
</dl>

<dl>
<dd>

**block_ids:** `typing.Optional[typing.Sequence[str]]` — The IDs of the blocks associated with the identity.
    
</dd>
</dl>

<dl>
<dd>

**properties:** `typing.Optional[typing.Sequence[IdentityProperty]]` — List of properties associated with the identity.
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.identities.<a href="src/letta_client/identities/client.py">retrieve</a>(...)</code></summary>
<dl>
<dd>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.identities.retrieve(
    identity_id="identity_id",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**identity_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.identities.<a href="src/letta_client/identities/client.py">delete</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Delete an identity by its identifier key
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.identities.delete(
    identity_id="identity_id",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**identity_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.identities.<a href="src/letta_client/identities/client.py">modify</a>(...)</code></summary>
<dl>
<dd>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.identities.modify(
    identity_id="identity_id",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**identity_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**identifier_key:** `typing.Optional[str]` — External, user-generated identifier key of the identity.
    
</dd>
</dl>

<dl>
<dd>

**name:** `typing.Optional[str]` — The name of the identity.
    
</dd>
</dl>

<dl>
<dd>

**identity_type:** `typing.Optional[IdentityType]` — The type of the identity.
    
</dd>
</dl>

<dl>
<dd>

**agent_ids:** `typing.Optional[typing.Sequence[str]]` — The agent ids that are associated with the identity.
    
</dd>
</dl>

<dl>
<dd>

**block_ids:** `typing.Optional[typing.Sequence[str]]` — The IDs of the blocks associated with the identity.
    
</dd>
</dl>

<dl>
<dd>

**properties:** `typing.Optional[typing.Sequence[IdentityProperty]]` — List of properties associated with the identity.
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

## Models
<details><summary><code>client.models.<a href="src/letta_client/models/client.py">list_llms</a>()</code></summary>
<dl>
<dd>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.models.list_llms()

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.models.<a href="src/letta_client/models/client.py">list_embedding_models</a>()</code></summary>
<dl>
<dd>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.models.list_embedding_models()

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

## Blocks
<details><summary><code>client.blocks.<a href="src/letta_client/blocks/client.py">list</a>(...)</code></summary>
<dl>
<dd>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.blocks.list()

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**label:** `typing.Optional[str]` — Labels to include (e.g. human, persona)
    
</dd>
</dl>

<dl>
<dd>

**templates_only:** `typing.Optional[bool]` — Whether to include only templates
    
</dd>
</dl>

<dl>
<dd>

**name:** `typing.Optional[str]` — Name of the block
    
</dd>
</dl>

<dl>
<dd>

**identity_id:** `typing.Optional[str]` — Search agents by identifier id
    
</dd>
</dl>

<dl>
<dd>

**identifier_keys:** `typing.Optional[typing.Union[str, typing.Sequence[str]]]` — Search agents by identifier keys
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.blocks.<a href="src/letta_client/blocks/client.py">create</a>(...)</code></summary>
<dl>
<dd>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.blocks.create(
    value="value",
    label="label",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**value:** `str` — Value of the block.
    
</dd>
</dl>

<dl>
<dd>

**label:** `str` — Label of the block.
    
</dd>
</dl>

<dl>
<dd>

**limit:** `typing.Optional[int]` — Character limit of the block.
    
</dd>
</dl>

<dl>
<dd>

**name:** `typing.Optional[str]` — Name of the block if it is a template.
    
</dd>
</dl>

<dl>
<dd>

**is_template:** `typing.Optional[bool]` 
    
</dd>
</dl>

<dl>
<dd>

**description:** `typing.Optional[str]` — Description of the block.
    
</dd>
</dl>

<dl>
<dd>

**metadata:** `typing.Optional[typing.Dict[str, typing.Optional[typing.Any]]]` — Metadata of the block.
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.blocks.<a href="src/letta_client/blocks/client.py">retrieve</a>(...)</code></summary>
<dl>
<dd>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.blocks.retrieve(
    block_id="block_id",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**block_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.blocks.<a href="src/letta_client/blocks/client.py">delete</a>(...)</code></summary>
<dl>
<dd>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.blocks.delete(
    block_id="block_id",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**block_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.blocks.<a href="src/letta_client/blocks/client.py">modify</a>(...)</code></summary>
<dl>
<dd>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.blocks.modify(
    block_id="block_id",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**block_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**value:** `typing.Optional[str]` — Value of the block.
    
</dd>
</dl>

<dl>
<dd>

**limit:** `typing.Optional[int]` — Character limit of the block.
    
</dd>
</dl>

<dl>
<dd>

**name:** `typing.Optional[str]` — Name of the block if it is a template.
    
</dd>
</dl>

<dl>
<dd>

**is_template:** `typing.Optional[bool]` — Whether the block is a template (e.g. saved human/persona options).
    
</dd>
</dl>

<dl>
<dd>

**label:** `typing.Optional[str]` — Label of the block (e.g. 'human', 'persona') in the context window.
    
</dd>
</dl>

<dl>
<dd>

**description:** `typing.Optional[str]` — Description of the block.
    
</dd>
</dl>

<dl>
<dd>

**metadata:** `typing.Optional[typing.Dict[str, typing.Optional[typing.Any]]]` — Metadata of the block.
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.blocks.<a href="src/letta_client/blocks/client.py">list_agents_for_block</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Retrieves all agents associated with the specified block.
Raises a 404 if the block does not exist.
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.blocks.list_agents_for_block(
    block_id="block_id",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**block_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

## Jobs
<details><summary><code>client.jobs.<a href="src/letta_client/jobs/client.py">list</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

List all jobs.
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.jobs.list()

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**source_id:** `typing.Optional[str]` — Only list jobs associated with the source.
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.jobs.<a href="src/letta_client/jobs/client.py">list_active</a>()</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

List all active jobs.
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.jobs.list_active()

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.jobs.<a href="src/letta_client/jobs/client.py">retrieve</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Get the status of a job.
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.jobs.retrieve(
    job_id="job_id",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**job_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.jobs.<a href="src/letta_client/jobs/client.py">delete</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Delete a job by its job_id.
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.jobs.delete(
    job_id="job_id",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**job_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

## Health
<details><summary><code>client.health.<a href="src/letta_client/health/client.py">check</a>()</code></summary>
<dl>
<dd>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.health.check()

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

## Providers
<details><summary><code>client.providers.<a href="src/letta_client/providers/client.py">list_providers</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Get a list of all custom providers in the database
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.providers.list_providers()

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**after:** `typing.Optional[str]` 
    
</dd>
</dl>

<dl>
<dd>

**limit:** `typing.Optional[int]` 
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.providers.<a href="src/letta_client/providers/client.py">create_provider</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Create a new custom provider
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.providers.create_provider(
    name="name",
    api_key="api_key",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**name:** `str` — The name of the provider.
    
</dd>
</dl>

<dl>
<dd>

**api_key:** `str` — API key used for requests to the provider.
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.providers.<a href="src/letta_client/providers/client.py">delete_provider</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Delete an existing custom provider
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.providers.delete_provider(
    provider_id="provider_id",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**provider_id:** `str` — The provider_id key to be deleted.
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.providers.<a href="src/letta_client/providers/client.py">modify_provider</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Update an existing custom provider
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.providers.modify_provider(
    id="id",
    api_key="api_key",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**id:** `str` — The id of the provider to update.
    
</dd>
</dl>

<dl>
<dd>

**api_key:** `str` — API key used for requests to the provider.
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

## Runs
<details><summary><code>client.runs.<a href="src/letta_client/runs/client.py">list_runs</a>()</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

List all runs.
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.runs.list_runs()

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.runs.<a href="src/letta_client/runs/client.py">list_active_runs</a>()</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

List all active runs.
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.runs.list_active_runs()

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.runs.<a href="src/letta_client/runs/client.py">retrieve_run</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Get the status of a run.
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.runs.retrieve_run(
    run_id="run_id",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**run_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.runs.<a href="src/letta_client/runs/client.py">delete_run</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Delete a run by its run_id.
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.runs.delete_run(
    run_id="run_id",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**run_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.runs.<a href="src/letta_client/runs/client.py">list_run_messages</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Get messages associated with a run with filtering options.

Args:
    run_id: ID of the run
    before: A cursor for use in pagination. `before` is an object ID that defines your place in the list. For instance, if you make a list request and receive 100 objects, starting with obj_foo, your subsequent call can include before=obj_foo in order to fetch the previous page of the list.
    after: A cursor for use in pagination. `after` is an object ID that defines your place in the list. For instance, if you make a list request and receive 100 objects, ending with obj_foo, your subsequent call can include after=obj_foo in order to fetch the next page of the list.
    limit: Maximum number of messages to return
    order: Sort order by the created_at timestamp of the objects. asc for ascending order and desc for descending order.
    role: Filter by role (user/assistant/system/tool)
    return_message_object: Whether to return Message objects or LettaMessage objects
    user_id: ID of the user making the request

Returns:
    A list of messages associated with the run. Default is List[LettaMessage].
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.runs.list_run_messages(
    run_id="run_id",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**run_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**before:** `typing.Optional[str]` — Cursor for pagination
    
</dd>
</dl>

<dl>
<dd>

**after:** `typing.Optional[str]` — Cursor for pagination
    
</dd>
</dl>

<dl>
<dd>

**limit:** `typing.Optional[int]` — Maximum number of messages to return
    
</dd>
</dl>

<dl>
<dd>

**order:** `typing.Optional[str]` — Sort order by the created_at timestamp of the objects. asc for ascending order and desc for descending order.
    
</dd>
</dl>

<dl>
<dd>

**role:** `typing.Optional[MessageRole]` — Filter by role
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.runs.<a href="src/letta_client/runs/client.py">retrieve_run_usage</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Get usage statistics for a run.
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.runs.retrieve_run_usage(
    run_id="run_id",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**run_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.runs.<a href="src/letta_client/runs/client.py">list_run_steps</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Get messages associated with a run with filtering options.

Args:
    run_id: ID of the run
    before: A cursor for use in pagination. `before` is an object ID that defines your place in the list. For instance, if you make a list request and receive 100 objects, starting with obj_foo, your subsequent call can include before=obj_foo in order to fetch the previous page of the list.
    after: A cursor for use in pagination. `after` is an object ID that defines your place in the list. For instance, if you make a list request and receive 100 objects, ending with obj_foo, your subsequent call can include after=obj_foo in order to fetch the next page of the list.
    limit: Maximum number of steps to return
    order: Sort order by the created_at timestamp of the objects. asc for ascending order and desc for descending order.

Returns:
    A list of steps associated with the run.
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.runs.list_run_steps(
    run_id="run_id",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**run_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**before:** `typing.Optional[str]` — Cursor for pagination
    
</dd>
</dl>

<dl>
<dd>

**after:** `typing.Optional[str]` — Cursor for pagination
    
</dd>
</dl>

<dl>
<dd>

**limit:** `typing.Optional[int]` — Maximum number of messages to return
    
</dd>
</dl>

<dl>
<dd>

**order:** `typing.Optional[str]` — Sort order by the created_at timestamp of the objects. asc for ascending order and desc for descending order.
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

## Steps
<details><summary><code>client.steps.<a href="src/letta_client/steps/client.py">list_steps</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

List steps with optional pagination and date filters.
Dates should be provided in ISO 8601 format (e.g. 2025-01-29T15:01:19-08:00)
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.steps.list_steps()

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**before:** `typing.Optional[str]` — Return steps before this step ID
    
</dd>
</dl>

<dl>
<dd>

**after:** `typing.Optional[str]` — Return steps after this step ID
    
</dd>
</dl>

<dl>
<dd>

**limit:** `typing.Optional[int]` — Maximum number of steps to return
    
</dd>
</dl>

<dl>
<dd>

**order:** `typing.Optional[str]` — Sort order (asc or desc)
    
</dd>
</dl>

<dl>
<dd>

**start_date:** `typing.Optional[str]` — Return steps after this ISO datetime (e.g. "2025-01-29T15:01:19-08:00")
    
</dd>
</dl>

<dl>
<dd>

**end_date:** `typing.Optional[str]` — Return steps before this ISO datetime (e.g. "2025-01-29T15:01:19-08:00")
    
</dd>
</dl>

<dl>
<dd>

**model:** `typing.Optional[str]` — Filter by the name of the model used for the step
    
</dd>
</dl>

<dl>
<dd>

**agent_id:** `typing.Optional[str]` — Filter by the ID of the agent that performed the step
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.steps.<a href="src/letta_client/steps/client.py">retrieve_step</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Get a step by ID.
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.steps.retrieve_step(
    step_id="step_id",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**step_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

## Tag
<details><summary><code>client.tag.<a href="src/letta_client/tag/client.py">list_tags</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Get a list of all tags in the database
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.tag.list_tags()

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**after:** `typing.Optional[str]` 
    
</dd>
</dl>

<dl>
<dd>

**limit:** `typing.Optional[int]` 
    
</dd>
</dl>

<dl>
<dd>

**query_text:** `typing.Optional[str]` 
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

## Voice
<details><summary><code>client.voice.<a href="src/letta_client/voice/client.py">create_voice_chat_completions</a>(...)</code></summary>
<dl>
<dd>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import (
    ChatCompletionDeveloperMessageParam,
    CompletionCreateParamsNonStreaming,
    Letta,
)

client = Letta(
    token="YOUR_TOKEN",
)
client.voice.create_voice_chat_completions(
    agent_id="agent_id",
    request=CompletionCreateParamsNonStreaming(
        messages=[
            ChatCompletionDeveloperMessageParam(
                content="content",
            )
        ],
        model="model",
    ),
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**agent_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**request:** `CreateVoiceChatCompletionsRequestBody` 
    
</dd>
</dl>

<dl>
<dd>

**user_id:** `typing.Optional[str]` 
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

## Templates
<details><summary><code>client.templates.<a href="src/letta_client/templates/client.py">create_agents</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Creates an Agent or multiple Agents from a template
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.templates.create_agents(
    project="project",
    template_version="template_version",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**project:** `str` — The project slug
    
</dd>
</dl>

<dl>
<dd>

**template_version:** `str` — The template version, formatted as {template-name}:{version-number} or {template-name}:latest
    
</dd>
</dl>

<dl>
<dd>

**tags:** `typing.Optional[typing.Sequence[str]]` — The tags to assign to the agent
    
</dd>
</dl>

<dl>
<dd>

**agent_name:** `typing.Optional[str]` — The name of the agent, optional otherwise a random one will be assigned
    
</dd>
</dl>

<dl>
<dd>

**memory_variables:** `typing.Optional[typing.Dict[str, str]]` — The memory variables to assign to the agent
    
</dd>
</dl>

<dl>
<dd>

**tool_variables:** `typing.Optional[typing.Dict[str, str]]` — The tool variables to assign to the agent
    
</dd>
</dl>

<dl>
<dd>

**identity_ids:** `typing.Optional[typing.Sequence[str]]` — The identity ids to assign to the agent
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

## Agents Context
<details><summary><code>client.agents.context.<a href="src/letta_client/agents/context/client.py">retrieve</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Retrieve the context window of a specific agent.
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.agents.context.retrieve(
    agent_id="agent_id",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**agent_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

## Agents Tools
<details><summary><code>client.agents.tools.<a href="src/letta_client/agents/tools/client.py">list</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Get tools from an existing agent
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.agents.tools.list(
    agent_id="agent_id",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**agent_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.agents.tools.<a href="src/letta_client/agents/tools/client.py">attach</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Attach a tool to an agent.
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.agents.tools.attach(
    agent_id="agent_id",
    tool_id="tool_id",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**agent_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**tool_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.agents.tools.<a href="src/letta_client/agents/tools/client.py">detach</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Detach a tool from an agent.
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.agents.tools.detach(
    agent_id="agent_id",
    tool_id="tool_id",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**agent_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**tool_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

## Agents Sources
<details><summary><code>client.agents.sources.<a href="src/letta_client/agents/sources/client.py">attach</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Attach a source to an agent.
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.agents.sources.attach(
    agent_id="agent_id",
    source_id="source_id",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**agent_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**source_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.agents.sources.<a href="src/letta_client/agents/sources/client.py">detach</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Detach a source from an agent.
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.agents.sources.detach(
    agent_id="agent_id",
    source_id="source_id",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**agent_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**source_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.agents.sources.<a href="src/letta_client/agents/sources/client.py">list</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Get the sources associated with an agent.
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.agents.sources.list(
    agent_id="agent_id",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**agent_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

## Agents CoreMemory
<details><summary><code>client.agents.core_memory.<a href="src/letta_client/agents/core_memory/client.py">retrieve</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Retrieve the memory state of a specific agent.
This endpoint fetches the current memory state of the agent identified by the user ID and agent ID.
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.agents.core_memory.retrieve(
    agent_id="agent_id",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**agent_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

## Agents Blocks
<details><summary><code>client.agents.blocks.<a href="src/letta_client/agents/blocks/client.py">retrieve</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Retrieve a core memory block from an agent.
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.agents.blocks.retrieve(
    agent_id="agent_id",
    block_label="block_label",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**agent_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**block_label:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.agents.blocks.<a href="src/letta_client/agents/blocks/client.py">modify</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Updates a core memory block of an agent.
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.agents.blocks.modify(
    agent_id="agent_id",
    block_label="block_label",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**agent_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**block_label:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**value:** `typing.Optional[str]` — Value of the block.
    
</dd>
</dl>

<dl>
<dd>

**limit:** `typing.Optional[int]` — Character limit of the block.
    
</dd>
</dl>

<dl>
<dd>

**name:** `typing.Optional[str]` — Name of the block if it is a template.
    
</dd>
</dl>

<dl>
<dd>

**is_template:** `typing.Optional[bool]` — Whether the block is a template (e.g. saved human/persona options).
    
</dd>
</dl>

<dl>
<dd>

**label:** `typing.Optional[str]` — Label of the block (e.g. 'human', 'persona') in the context window.
    
</dd>
</dl>

<dl>
<dd>

**description:** `typing.Optional[str]` — Description of the block.
    
</dd>
</dl>

<dl>
<dd>

**metadata:** `typing.Optional[typing.Dict[str, typing.Optional[typing.Any]]]` — Metadata of the block.
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.agents.blocks.<a href="src/letta_client/agents/blocks/client.py">list</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Retrieve the core memory blocks of a specific agent.
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.agents.blocks.list(
    agent_id="agent_id",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**agent_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.agents.blocks.<a href="src/letta_client/agents/blocks/client.py">attach</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Attach a core memoryblock to an agent.
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.agents.blocks.attach(
    agent_id="agent_id",
    block_id="block_id",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**agent_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**block_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.agents.blocks.<a href="src/letta_client/agents/blocks/client.py">detach</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Detach a core memory block from an agent.
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.agents.blocks.detach(
    agent_id="agent_id",
    block_id="block_id",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**agent_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**block_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

## Agents Passages
<details><summary><code>client.agents.passages.<a href="src/letta_client/agents/passages/client.py">list</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Retrieve the memories in an agent's archival memory store (paginated query).
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.agents.passages.list(
    agent_id="agent_id",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**agent_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**after:** `typing.Optional[str]` — Unique ID of the memory to start the query range at.
    
</dd>
</dl>

<dl>
<dd>

**before:** `typing.Optional[str]` — Unique ID of the memory to end the query range at.
    
</dd>
</dl>

<dl>
<dd>

**limit:** `typing.Optional[int]` — How many results to include in the response.
    
</dd>
</dl>

<dl>
<dd>

**search:** `typing.Optional[str]` — Search passages by text
    
</dd>
</dl>

<dl>
<dd>

**ascending:** `typing.Optional[bool]` — Whether to sort passages oldest to newest (True, default) or newest to oldest (False)
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.agents.passages.<a href="src/letta_client/agents/passages/client.py">create</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Insert a memory into an agent's archival memory store.
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.agents.passages.create(
    agent_id="agent_id",
    text="text",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**agent_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**text:** `str` — Text to write to archival memory.
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.agents.passages.<a href="src/letta_client/agents/passages/client.py">delete</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Delete a memory from an agent's archival memory store.
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.agents.passages.delete(
    agent_id="agent_id",
    memory_id="memory_id",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**agent_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**memory_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

## Agents Messages
<details><summary><code>client.agents.messages.<a href="src/letta_client/agents/messages/client.py">list</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Retrieve message history for an agent.
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.agents.messages.list(
    agent_id="agent_id",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**agent_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**after:** `typing.Optional[str]` — Message after which to retrieve the returned messages.
    
</dd>
</dl>

<dl>
<dd>

**before:** `typing.Optional[str]` — Message before which to retrieve the returned messages.
    
</dd>
</dl>

<dl>
<dd>

**limit:** `typing.Optional[int]` — Maximum number of messages to retrieve.
    
</dd>
</dl>

<dl>
<dd>

**group_id:** `typing.Optional[str]` — Group ID to filter messages by.
    
</dd>
</dl>

<dl>
<dd>

**use_assistant_message:** `typing.Optional[bool]` — Whether to use assistant messages
    
</dd>
</dl>

<dl>
<dd>

**assistant_message_tool_name:** `typing.Optional[str]` — The name of the designated message tool.
    
</dd>
</dl>

<dl>
<dd>

**assistant_message_tool_kwarg:** `typing.Optional[str]` — The name of the message argument.
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.agents.messages.<a href="src/letta_client/agents/messages/client.py">create</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Process a user message and return the agent's response.
This endpoint accepts a message from a user and processes it through the agent.
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta, MessageCreate, TextContent

client = Letta(
    token="YOUR_TOKEN",
)
client.agents.messages.create(
    agent_id="agent_id",
    messages=[
        MessageCreate(
            role="user",
            content=[
                TextContent(
                    text="text",
                )
            ],
        )
    ],
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**agent_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**messages:** `typing.Sequence[MessageCreate]` — The messages to be sent to the agent.
    
</dd>
</dl>

<dl>
<dd>

**use_assistant_message:** `typing.Optional[bool]` — Whether the server should parse specific tool call arguments (default `send_message`) as `AssistantMessage` objects.
    
</dd>
</dl>

<dl>
<dd>

**assistant_message_tool_name:** `typing.Optional[str]` — The name of the designated message tool.
    
</dd>
</dl>

<dl>
<dd>

**assistant_message_tool_kwarg:** `typing.Optional[str]` — The name of the message argument in the designated message tool.
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.agents.messages.<a href="src/letta_client/agents/messages/client.py">modify</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Update the details of a message associated with an agent.
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta, UpdateSystemMessage

client = Letta(
    token="YOUR_TOKEN",
)
client.agents.messages.modify(
    agent_id="agent_id",
    message_id="message_id",
    request=UpdateSystemMessage(
        content="content",
    ),
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**agent_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**message_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**request:** `MessagesModifyRequest` 
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.agents.messages.<a href="src/letta_client/agents/messages/client.py">create_stream</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Process a user message and return the agent's response.
This endpoint accepts a message from a user and processes it through the agent.
It will stream the steps of the response always, and stream the tokens if 'stream_tokens' is set to True.
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta, MessageCreate, TextContent

client = Letta(
    token="YOUR_TOKEN",
)
response = client.agents.messages.create_stream(
    agent_id="agent_id",
    messages=[
        MessageCreate(
            role="user",
            content=[
                TextContent(
                    text="text",
                )
            ],
        )
    ],
)
for chunk in response:
    yield chunk

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**agent_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**messages:** `typing.Sequence[MessageCreate]` — The messages to be sent to the agent.
    
</dd>
</dl>

<dl>
<dd>

**use_assistant_message:** `typing.Optional[bool]` — Whether the server should parse specific tool call arguments (default `send_message`) as `AssistantMessage` objects.
    
</dd>
</dl>

<dl>
<dd>

**assistant_message_tool_name:** `typing.Optional[str]` — The name of the designated message tool.
    
</dd>
</dl>

<dl>
<dd>

**assistant_message_tool_kwarg:** `typing.Optional[str]` — The name of the message argument in the designated message tool.
    
</dd>
</dl>

<dl>
<dd>

**stream_tokens:** `typing.Optional[bool]` — Flag to determine if individual tokens should be streamed. Set to True for token streaming (requires stream_steps = True).
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.agents.messages.<a href="src/letta_client/agents/messages/client.py">create_async</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Asynchronously process a user message and return a run object.
The actual processing happens in the background, and the status can be checked using the run ID.
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta, MessageCreate, TextContent

client = Letta(
    token="YOUR_TOKEN",
)
client.agents.messages.create_async(
    agent_id="agent_id",
    messages=[
        MessageCreate(
            role="user",
            content=[
                TextContent(
                    text="text",
                )
            ],
        )
    ],
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**agent_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**messages:** `typing.Sequence[MessageCreate]` — The messages to be sent to the agent.
    
</dd>
</dl>

<dl>
<dd>

**use_assistant_message:** `typing.Optional[bool]` — Whether the server should parse specific tool call arguments (default `send_message`) as `AssistantMessage` objects.
    
</dd>
</dl>

<dl>
<dd>

**assistant_message_tool_name:** `typing.Optional[str]` — The name of the designated message tool.
    
</dd>
</dl>

<dl>
<dd>

**assistant_message_tool_kwarg:** `typing.Optional[str]` — The name of the message argument in the designated message tool.
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

## Agents Templates
<details><summary><code>client.agents.templates.<a href="src/letta_client/agents/templates/client.py">create_version</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

<Note>This endpoint is only available on Letta Cloud.</Note>

Creates a new version of the template version of the agent.
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.agents.templates.create_version(
    agent_id="agent_id",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**agent_id:** `str` — The agent ID of the agent to migrate, if this agent is not a template, it will create a agent template from the agent provided as well
    
</dd>
</dl>

<dl>
<dd>

**return_agent_state:** `typing.Optional[bool]` 
    
</dd>
</dl>

<dl>
<dd>

**migrate_deployed_agents:** `typing.Optional[bool]` 
    
</dd>
</dl>

<dl>
<dd>

**message:** `typing.Optional[str]` 
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.agents.templates.<a href="src/letta_client/agents/templates/client.py">migrate</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

<Note>This endpoint is only available on Letta Cloud.</Note>

Migrate an agent to a new versioned agent template.
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.agents.templates.migrate(
    agent_id="agent_id",
    to_template="to_template",
    preserve_core_memories=True,
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**agent_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**to_template:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**preserve_core_memories:** `bool` 
    
</dd>
</dl>

<dl>
<dd>

**variables:** `typing.Optional[typing.Dict[str, str]]` — If you chose to not preserve core memories, you should provide the new variables for the core memories
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.agents.templates.<a href="src/letta_client/agents/templates/client.py">create</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

<Note>This endpoint is only available on Letta Cloud.</Note>

Creates a template from an agent.
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.agents.templates.create(
    agent_id="agent_id",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**agent_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**project:** `typing.Optional[str]` 
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

## Agents MemoryVariables
<details><summary><code>client.agents.memory_variables.<a href="src/letta_client/agents/memory_variables/client.py">list</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

<Note>This endpoint is only available on Letta Cloud.</Note>

Returns the memory variables associated with an agent.
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.agents.memory_variables.list(
    agent_id="agent_id",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**agent_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

## Groups Messages
<details><summary><code>client.groups.messages.<a href="src/letta_client/groups/messages/client.py">list</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Retrieve message history for an agent.
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.groups.messages.list(
    group_id="group_id",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**group_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**after:** `typing.Optional[str]` — Message after which to retrieve the returned messages.
    
</dd>
</dl>

<dl>
<dd>

**before:** `typing.Optional[str]` — Message before which to retrieve the returned messages.
    
</dd>
</dl>

<dl>
<dd>

**limit:** `typing.Optional[int]` — Maximum number of messages to retrieve.
    
</dd>
</dl>

<dl>
<dd>

**use_assistant_message:** `typing.Optional[bool]` — Whether to use assistant messages
    
</dd>
</dl>

<dl>
<dd>

**assistant_message_tool_name:** `typing.Optional[str]` — The name of the designated message tool.
    
</dd>
</dl>

<dl>
<dd>

**assistant_message_tool_kwarg:** `typing.Optional[str]` — The name of the message argument.
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.groups.messages.<a href="src/letta_client/groups/messages/client.py">create</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Process a user message and return the group's response.
This endpoint accepts a message from a user and processes it through through agents in the group based on the specified pattern
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta, MessageCreate, TextContent

client = Letta(
    token="YOUR_TOKEN",
)
client.groups.messages.create(
    group_id="group_id",
    messages=[
        MessageCreate(
            role="user",
            content=[
                TextContent(
                    text="text",
                )
            ],
        )
    ],
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**group_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**messages:** `typing.Sequence[MessageCreate]` — The messages to be sent to the agent.
    
</dd>
</dl>

<dl>
<dd>

**use_assistant_message:** `typing.Optional[bool]` — Whether the server should parse specific tool call arguments (default `send_message`) as `AssistantMessage` objects.
    
</dd>
</dl>

<dl>
<dd>

**assistant_message_tool_name:** `typing.Optional[str]` — The name of the designated message tool.
    
</dd>
</dl>

<dl>
<dd>

**assistant_message_tool_kwarg:** `typing.Optional[str]` — The name of the message argument in the designated message tool.
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.groups.messages.<a href="src/letta_client/groups/messages/client.py">create_stream</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Process a user message and return the group's responses.
This endpoint accepts a message from a user and processes it through agents in the group based on the specified pattern.
It will stream the steps of the response always, and stream the tokens if 'stream_tokens' is set to True.
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta, MessageCreate, TextContent

client = Letta(
    token="YOUR_TOKEN",
)
response = client.groups.messages.create_stream(
    group_id="group_id",
    messages=[
        MessageCreate(
            role="user",
            content=[
                TextContent(
                    text="text",
                )
            ],
        )
    ],
)
for chunk in response:
    yield chunk

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**group_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**messages:** `typing.Sequence[MessageCreate]` — The messages to be sent to the agent.
    
</dd>
</dl>

<dl>
<dd>

**use_assistant_message:** `typing.Optional[bool]` — Whether the server should parse specific tool call arguments (default `send_message`) as `AssistantMessage` objects.
    
</dd>
</dl>

<dl>
<dd>

**assistant_message_tool_name:** `typing.Optional[str]` — The name of the designated message tool.
    
</dd>
</dl>

<dl>
<dd>

**assistant_message_tool_kwarg:** `typing.Optional[str]` — The name of the message argument in the designated message tool.
    
</dd>
</dl>

<dl>
<dd>

**stream_tokens:** `typing.Optional[bool]` — Flag to determine if individual tokens should be streamed. Set to True for token streaming (requires stream_steps = True).
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.groups.messages.<a href="src/letta_client/groups/messages/client.py">modify</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Update the details of a message associated with an agent.
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta, UpdateSystemMessage

client = Letta(
    token="YOUR_TOKEN",
)
client.groups.messages.modify(
    group_id="group_id",
    message_id="message_id",
    request=UpdateSystemMessage(
        content="content",
    ),
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**group_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**message_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**request:** `MessagesModifyRequest` 
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

## Sources Files
<details><summary><code>client.sources.files.<a href="src/letta_client/sources/files/client.py">upload</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Upload a file to a data source.
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.sources.files.upload(
    source_id="source_id",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**source_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**file:** `from __future__ import annotations

core.File` — See core.File for more documentation
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.sources.files.<a href="src/letta_client/sources/files/client.py">list</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

List paginated files associated with a data source.
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.sources.files.list(
    source_id="source_id",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**source_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**limit:** `typing.Optional[int]` — Number of files to return
    
</dd>
</dl>

<dl>
<dd>

**after:** `typing.Optional[str]` — Pagination cursor to fetch the next set of results
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.sources.files.<a href="src/letta_client/sources/files/client.py">delete</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Delete a data source.
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.sources.files.delete(
    source_id="source_id",
    file_id="file_id",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**source_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**file_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

## Sources Passages
<details><summary><code>client.sources.passages.<a href="src/letta_client/sources/passages/client.py">list</a>(...)</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

List all passages associated with a data source.
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```python
from letta_client import Letta

client = Letta(
    token="YOUR_TOKEN",
)
client.sources.passages.list(
    source_id="source_id",
)

```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**source_id:** `str` 
    
</dd>
</dl>

<dl>
<dd>

**request_options:** `typing.Optional[RequestOptions]` — Request-specific configuration.
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>
