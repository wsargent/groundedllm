/**
 * Tool handler for listing agents in the Letta system
 */
export async function handleListAgents(server, args) {
    try {
        // Headers for API requests
        const headers = server.getApiHeaders();

        // Get the list of agents
        const response = await server.api.get('/agents', { headers });
        const agents = response.data;

        // Apply filter if provided
        let filteredAgents = agents;
        if (args?.filter) {
            const filter = args.filter.toLowerCase();
            filteredAgents = agents.filter(agent => 
                agent.name.toLowerCase().includes(filter) ||
                (agent.description && agent.description.toLowerCase().includes(filter))
            );
        }

        return {
            content: [{
                type: 'text',
                text: JSON.stringify({
                    success: true,
                    count: filteredAgents.length,
                    agents: filteredAgents
                }, null, 2),
            }],
        };
    } catch (error) {
        return server.createErrorResponse(error);
    }
}

/**
 * Tool definition for list_agents
 */
export const listAgentsToolDefinition = {
    name: 'list_agents',
    description: 'List all available agents in the Letta system',
    inputSchema: {
        type: 'object',
        properties: {
            filter: {
                type: 'string',
                description: 'Optional filter to search for specific agents',
            },
        },
        required: [],
    },
};