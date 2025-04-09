/**
 * Tool handler for attaching a memory block to an agent in the Letta system
 */
export async function handleAttachMemoryBlock(server, args) {
    try {
        // Validate arguments
        if (!args.block_id) {
            throw new Error('Missing required argument: block_id');
        }
        if (!args.agent_id) {
            throw new Error('Missing required argument: agent_id');
        }
        
        // Headers for API requests
        const headers = server.getApiHeaders();
        headers['user_id'] = args.agent_id;
        
        // Verify block exists
        const blockResponse = await server.api.get(`/blocks/${args.block_id}`, { headers });
        const blockData = blockResponse.data;
        const blockName = blockData.name || 'Unnamed Block';
        
        // Determine label to use
        const label = args.label || blockData.label || 'custom';
        
        // Attach block to agent
        console.log(`Attaching memory block ${blockName} (${args.block_id}) to agent ${args.agent_id} with label ${label}...`);
        
        // Use the core-memory/blocks/attach endpoint
        const attachUrl = `/agents/${args.agent_id}/core-memory/blocks/attach/${args.block_id}`;
        
        // Send an empty object as the request body
        const response = await server.api.patch(attachUrl, {}, { headers });
        
        // Get updated agent data to verify attachment
        const agentInfoResponse = await server.api.get(`/agents/${args.agent_id}`, { headers });
        const agentData = agentInfoResponse.data;
        const agentName = agentData.name || 'Unknown';
        
        // Format the response
        return {
            content: [{
                type: 'text',
                text: JSON.stringify({
                    success: true,
                    message: `Memory block ${blockName} successfully attached to agent ${agentName} with label ${label}.`,
                    agent_id: args.agent_id,
                    agent_name: agentName,
                    block_id: args.block_id,
                    block_name: blockName,
                    label: label
                }, null, 2),
            }],
        };
    } catch (error) {
        return server.createErrorResponse(error);
    }
}

/**
 * Tool definition for attach_memory_block
 */
export const attachMemoryBlockToolDefinition = {
    name: 'attach_memory_block',
    description: 'Attach a memory block to an agent',
    inputSchema: {
        type: 'object',
        properties: {
            block_id: {
                type: 'string',
                description: 'The ID of the memory block to attach',
            },
            agent_id: {
                type: 'string',
                description: 'The ID of the agent to attach the memory block to',
            },
            label: {
                type: 'string',
                description: 'Optional label for the memory block (e.g., "persona", "human", "system")',
            },
        },
        required: ['block_id', 'agent_id'],
    },
};