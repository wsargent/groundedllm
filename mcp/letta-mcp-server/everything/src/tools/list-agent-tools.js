/**
 * Tool handler for listing tools available for a specific agent
 */
export async function handleListAgentTools(server, args) {
    try {
        if (!args.agent_id) {
            throw new Error('Missing required argument: agent_id');
        }

        const headers = server.getApiHeaders();

        const agentInfoResponse = await server.api.get(`/agents/${args.agent_id}`, { headers });
        const agentName = agentInfoResponse.data.name;
        const tools = agentInfoResponse.data.tools || [];

        return {
            content: [{
                type: 'text',
                text: JSON.stringify({
                    success: true,
                    agent_id: args.agent_id,
                    agent_name: agentName,
                    tool_count: tools.length,
                    tools: tools
                }, null, 2),
            }],
        };
    } catch (error) {
        return server.createErrorResponse(error);
    }
}

/**
 * Tool definition for list_agent_tools
 */
export const listAgentToolsDefinition = {
    name: 'list_agent_tools',
    description: 'List all tools available for a specific agent',
    inputSchema: {
        type: 'object',
        properties: {
            agent_id: {
                type: 'string',
                description: 'ID of the agent to list tools for',
            },
        },
        required: ['agent_id'],
    },
};