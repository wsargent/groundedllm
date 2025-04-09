/**
 * Tool handler for creating a new memory block in the Letta system
 */
export async function handleCreateMemoryBlock(server, args) {
    try {
        // Validate arguments
        if (!args.name || typeof args.name !== 'string') {
            throw new Error('Missing required argument: name (must be a string)');
        }
        if (!args.label || typeof args.label !== 'string') {
            throw new Error('Missing required argument: label (must be a string)');
        }
        if (!args.value || typeof args.value !== 'string') {
            throw new Error('Missing required argument: value (must be a string)');
        }
        
        // Headers for API requests
        const headers = server.getApiHeaders();
        
        // If agent_id is provided, set the user_id header
        if (args.agent_id) {
            headers['user_id'] = args.agent_id;
        }
        
        // Prepare metadata
        const metadata = args.metadata || {
            type: args.label,
            version: "1.0",
            last_updated: new Date().toISOString()
        };
        
        // Prepare block data
        const blockData = {
            name: args.name,
            label: args.label,
            value: args.value,
            metadata: metadata
        };
        
        // Create the memory block
        console.log(`Creating memory block "${args.name}" with label "${args.label}"...`);
        const createResponse = await server.api.post('/blocks', blockData, { headers });
        const blockId = createResponse.data.id;
        
        // If agent_id is provided, attach the block to the agent
        if (args.agent_id) {
            const attachUrl = `/agents/${args.agent_id}/core-memory/blocks/attach/${blockId}`;
            await server.api.patch(attachUrl, {}, { headers });
            
            // Get agent info
            const agentInfoResponse = await server.api.get(`/agents/${args.agent_id}`, { headers });
            const agentName = agentInfoResponse.data.name || 'Unknown';
            
            return {
                content: [{
                    type: 'text',
                    text: JSON.stringify({
                        success: true,
                        message: `Memory block "${args.name}" created and attached to agent ${agentName}.`,
                        block_id: blockId,
                        block_name: args.name,
                        agent_id: args.agent_id,
                        agent_name: agentName,
                        label: args.label
                    }, null, 2),
                }],
            };
        } else {
            // Just return the created block info
            return {
                content: [{
                    type: 'text',
                    text: JSON.stringify({
                        success: true,
                        message: `Memory block "${args.name}" created successfully.`,
                        block_id: blockId,
                        block_name: args.name,
                        label: args.label
                    }, null, 2),
                }],
            };
        }
    } catch (error) {
        return server.createErrorResponse(error);
    }
}

/**
 * Tool definition for create_memory_block
 */
export const createMemoryBlockToolDefinition = {
    name: 'create_memory_block',
    description: 'Create a new memory block in the Letta system',
    inputSchema: {
        type: 'object',
        properties: {
            name: {
                type: 'string',
                description: 'Name of the memory block',
            },
            label: {
                type: 'string',
                description: 'Label for the memory block (e.g., "persona", "human", "system")',
            },
            value: {
                type: 'string',
                description: 'Content of the memory block',
            },
            agent_id: {
                type: 'string',
                description: 'Optional agent ID to create the block for a specific agent',
            },
            metadata: {
                type: 'object',
                description: 'Optional metadata for the memory block',
            },
        },
        required: ['name', 'label', 'value'],
    },
};