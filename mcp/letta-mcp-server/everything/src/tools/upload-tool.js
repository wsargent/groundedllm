/**
 * Tool handler for uploading a new tool to the Letta system
 */
export async function handleUploadTool(server, args) {
    try {
        // Validate arguments
        if (!args.name || typeof args.name !== 'string') {
            throw new Error('Missing required argument: name (must be a string)');
        }
        if (!args.description || typeof args.description !== 'string') {
            throw new Error('Missing required argument: description (must be a string)');
        }
        if (!args.source_code || typeof args.source_code !== 'string') {
            throw new Error('Missing required argument: source_code (must be a string)');
        }
        
        // Headers for API requests
        const headers = server.getApiHeaders();
        
        // If agent_id is provided, set the user_id header
        if (args.agent_id) {
            headers['user_id'] = args.agent_id;
        }
        
        // Prepare category/tag
        const category = args.category || 'custom';
        
        // Check if tool exists and delete if found
        const toolsResponse = await server.api.get('/tools', { headers });
        const existingTools = toolsResponse.data;
        let existingToolId = null;
        
        for (const tool of existingTools) {
            if (tool.name === args.name) {
                existingToolId = tool.id;
                console.log(`Found existing tool ${args.name} with ID ${existingToolId}, will delete it first...`);
                break;
            }
        }
        
        if (existingToolId) {
            try {
                await server.api.delete(`/tools/${existingToolId}`, { headers });
                console.log(`Successfully deleted existing tool ${args.name}`);
            } catch (deleteError) {
                console.warn(`Failed to delete existing tool: ${deleteError}. Will try to continue anyway.`);
            }
        }
        
        // Prepare tool data
        const toolData = {
            source_code: args.source_code,
            description: args.description,
            tags: [category],
            source_type: "python"
        };
        
        // Create the tool
        console.log(`Creating tool "${args.name}"...`);
        const createResponse = await server.api.post('/tools', toolData, { headers });
        const toolId = createResponse.data.id;
        
        // If agent_id is provided, attach the tool to the agent
        if (args.agent_id) {
            // Attach tool to agent
            const attachUrl = `/agents/${args.agent_id}/tools/attach/${toolId}`;
            await server.api.patch(attachUrl, {}, { headers });
            
            // Get agent info
            const agentInfoResponse = await server.api.get(`/agents/${args.agent_id}`, { headers });
            const agentName = agentInfoResponse.data.name || 'Unknown';
            
            return {
                content: [{
                    type: 'text',
                    text: JSON.stringify({
                        success: true,
                        message: `Tool "${args.name}" created and attached to agent ${agentName}.`,
                        tool_id: toolId,
                        tool_name: args.name,
                        agent_id: args.agent_id,
                        agent_name: agentName,
                        category: category
                    }, null, 2),
                }],
            };
        } else {
            // Just return the created tool info
            return {
                content: [{
                    type: 'text',
                    text: JSON.stringify({
                        success: true,
                        message: `Tool "${args.name}" created successfully.`,
                        tool_id: toolId,
                        tool_name: args.name,
                        category: category
                    }, null, 2),
                }],
            };
        }
    } catch (error) {
        return server.createErrorResponse(error);
    }
}

/**
 * Tool definition for upload_tool
 */
export const uploadToolToolDefinition = {
    name: 'upload_tool',
    description: 'Upload a new tool to the Letta system',
    inputSchema: {
        type: 'object',
        properties: {
            name: {
                type: 'string',
                description: 'Name of the tool',
            },
            description: {
                type: 'string',
                description: 'Description of what the tool does',
            },
            source_code: {
                type: 'string',
                description: 'Python source code for the tool',
            },
            category: {
                type: 'string',
                description: 'Category/tag for the tool (e.g., "plane_api", "utility")',
                default: 'custom',
            },
            agent_id: {
                type: 'string',
                description: 'Optional agent ID to attach the tool to after creation',
            }
        },
        required: ['name', 'description', 'source_code'],
    },
};