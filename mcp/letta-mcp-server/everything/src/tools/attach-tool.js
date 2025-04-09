/**
 * Tool handler for attaching tools to an agent in the Letta system
 */
export async function handleAttachTool(server, args) {
    try {
        // Validate arguments
        if (!args.agent_id) {
            throw new Error('Missing required argument: agent_id');
        }
        
        // Determine tool IDs to attach
        let toolIds = [];
        if (args.tool_ids) {
            // Use the new tool_ids parameter
            toolIds = Array.isArray(args.tool_ids) ? args.tool_ids : [args.tool_ids];
        } else if (args.tool_id) {
            // Backward compatibility with the old tool_id parameter
            toolIds = [args.tool_id];
        } else {
            throw new Error('Missing required argument: either tool_id or tool_ids must be provided');
        }
        
        if (toolIds.length === 0) {
            throw new Error('No tool IDs provided');
        }
        
        // Headers for API requests
        const headers = server.getApiHeaders();
        headers['user_id'] = args.agent_id;
        
        // Get agent info to use in response
        const agentInfoResponse = await server.api.get(`/agents/${args.agent_id}`, { headers });
        const agentName = agentInfoResponse.data.name || 'Unknown';
        
        // Verify all tools exist before attaching any
        const toolsInfo = [];
        for (const toolId of toolIds) {
            try {
                const toolResponse = await server.api.get(`/tools/${toolId}`, { headers });
                toolsInfo.push({
                    id: toolId,
                    name: toolResponse.data.name || 'Unknown'
                });
            } catch (error) {
                throw new Error(`Tool ${toolId} not found: ${error.message}`);
            }
        }
        
        // Attach all tools
        const results = [];
        for (const tool of toolsInfo) {
            console.log(`Attaching tool ${tool.name} (${tool.id}) to agent ${args.agent_id}...`);
            const attachUrl = `/agents/${args.agent_id}/tools/attach/${tool.id}`;
            
            try {
                const response = await server.api.patch(attachUrl, {}, { headers });
                
                // Check if tool is now in agent's tools
                const attachedToolIds = response.data.tools?.map((t) => t.id) || [];
                if (attachedToolIds.includes(tool.id)) {
                    results.push({
                        success: true,
                        tool_id: tool.id,
                        tool_name: tool.name,
                        message: `Tool ${tool.name} successfully attached to agent ${agentName}.`
                    });
                } else {
                    results.push({
                        success: false,
                        tool_id: tool.id,
                        tool_name: tool.name,
                        error: `Tool ${tool.id} was not found in agent's tools after attachment.`
                    });
                }
            } catch (error) {
                results.push({
                    success: false,
                    tool_id: tool.id,
                    tool_name: tool.name,
                    error: error.message,
                    details: error.response?.data || error
                });
            }
        }
        
        // Check if all attachments were successful
        const allSuccessful = results.every(result => result.success);
        
        return {
            content: [{
                type: 'text',
                text: JSON.stringify({
                    success: allSuccessful,
                    message: allSuccessful
                        ? `Successfully attached ${results.length} tool(s) to agent ${agentName}.`
                        : `Some tools failed to attach to agent ${agentName}.`,
                    agent_id: args.agent_id,
                    agent_name: agentName,
                    total_tools: results.length,
                    successful_tools: results.filter(r => r.success).length,
                    failed_tools: results.filter(r => !r.success).length,
                    results: results
                }, null, 2),
            }],
            isError: !allSuccessful
        };
    } catch (error) {
        return server.createErrorResponse(error);
    }
}

/**
 * Tool definition for attach_tool
 */
export const attachToolToolDefinition = {
    name: 'attach_tool',
    description: 'Attach one or more tools to an agent',
    inputSchema: {
        type: 'object',
        properties: {
            tool_id: {
                type: 'string',
                description: 'The ID of a single tool to attach (deprecated, use tool_ids instead)',
            },
            tool_ids: {
                type: 'array',
                items: {
                    type: 'string'
                },
                description: 'Array of tool IDs to attach',
            },
            agent_id: {
                type: 'string',
                description: 'The ID of the agent to attach the tool(s) to',
            },
        },
        required: ['agent_id'],
    },
};