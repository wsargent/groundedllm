/**
 * Tool handler for listing all available tools on the Letta server
 */
export async function handleListTools(server, args) {
    try {
        const headers = server.getApiHeaders();

        const response = await server.api.get('/tools', { headers });
        let tools = response.data;

        if (args?.filter) {
            const filterLower = args.filter.toLowerCase();
            tools = tools.filter(tool => 
                (tool.name && tool.name.toLowerCase().includes(filterLower)) ||
                (tool.description && tool.description.toLowerCase().includes(filterLower))
            );
        }

        const page = args?.page || 1;
        const pageSize = args?.pageSize || 10;
        const startIndex = (page - 1) * pageSize;
        const endIndex = startIndex + pageSize;
        const totalTools = tools.length;
        const totalPages = Math.ceil(totalTools / pageSize);
        const paginatedTools = tools.slice(startIndex, endIndex);

        return {
            content: [{
                type: 'text',
                text: JSON.stringify({
                    success: true,
                    pagination: {
                        page,
                        pageSize,
                        totalTools,
                        totalPages,
                        hasNextPage: page < totalPages,
                        hasPreviousPage: page > 1
                    },
                    tool_count: paginatedTools.length,
                    tools: paginatedTools
                }, null, 2),
            }],
        };
    } catch (error) {
        return server.createErrorResponse(error);
    }
}

/**
 * Tool definition for list_tools
 */
export const listToolsDefinition = {
    name: 'list_tools',
    description: 'List all available tools on the Letta server',
    inputSchema: {
        type: 'object',
        properties: {
            filter: {
                type: 'string',
                description: 'Optional filter to search for specific tools by name or description',
            },
            page: {
                type: 'number',
                description: 'Page number for pagination (starts at 1)',
            },
            pageSize: {
                type: 'number',
                description: 'Number of tools per page (1-100, default: 10)',
            },
        },
        required: [],
    },
};