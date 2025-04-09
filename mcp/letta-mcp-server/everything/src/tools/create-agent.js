/**
 * Tool handler for creating a new agent in the Letta system
 */
export async function handleCreateAgent(server, args) {
    try {
        // Validate arguments
        if (!args.name || !args.description || typeof args.name !== 'string' || typeof args.description !== 'string') {
            throw new Error('Invalid arguments: name and description must be strings');
        }

        const model = args.model ?? 'openai/gpt-4';
        const embedding = args.embedding ?? 'openai/text-embedding-ada-002';

        // Agent configuration
        const agentConfig = {
            name: args.name,
            description: args.description,
            agent_type: "memgpt_agent",
            model: model,
            llm_config: {
                model: model.split('/')[1],
                model_endpoint_type: model.split('/')[0],
                context_window: 16000,
                max_tokens: 1000,
                temperature: 0.7,
                frequency_penalty: 0.5,
                presence_penalty: 0.5,
                functions_config: {
                    allow: true,
                    functions: []
                }
            },
            embedding: embedding,
            parameters: {
                context_window: 16000,
                max_tokens: 1000,
                temperature: 0.7,
                presence_penalty: 0.5,
                frequency_penalty: 0.5
            },
            core_memory: {}
        };

        // Headers for API requests
        const headers = server.getApiHeaders();

        // Create agent
        const createAgentResponse = await server.api.post('/agents', agentConfig, { headers });
        const agentId = createAgentResponse.data.id;

        // Update headers with agent ID
        headers['user_id'] = agentId;

        // Get agent info for the response
        const agentInfo = await server.api.get(`/agents/${agentId}`, { headers });
        const capabilities = agentInfo.data.tools?.map((t) => t.name) ?? [];

        return {
            content: [{
                type: 'text',
                text: JSON.stringify({
                    success: true,
                    message: `Agent ${args.name} created successfully with ID: ${agentId}`,
                    agent_id: agentId,
                    capabilities,
                }, null, 2),
            }],
        };
    } catch (error) {
        return server.createErrorResponse(error);
    }
}

/**
 * Tool definition for create_agent
 */
export const createAgentToolDefinition = {
    name: 'create_agent',
    description: 'Create a new Letta agent with specified configuration',
    inputSchema: {
        type: 'object',
        properties: {
            name: {
                type: 'string',
                description: 'Name of the new agent',
            },
            description: {
                type: 'string',
                description: 'Description of the agent\'s purpose/role',
            },
            model: {
                type: 'string',
                description: 'The model to use for the agent',
                default: 'openai/gpt-4',
            },
            embedding: {
                type: 'string',
                description: 'The embedding model to use',
                default: 'openai/text-embedding-ada-002',
            },
        },
        required: ['name', 'description'],
    },
};