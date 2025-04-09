import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';

/**
 * Run the server using stdio transport
 * @param {Object} server - The LettaServer instance
 */
export async function runStdio(server) {
    try {
        const transport = new StdioServerTransport();
        await server.server.connect(transport);
        console.error('Letta MCP server running on stdio');

        const cleanup = async () => {
            await server.server.close();
            process.exit(0);
        };

        process.on('SIGINT', cleanup);
        process.on('SIGTERM', cleanup);
        process.on('uncaughtException', async (error) => {
            console.error('Uncaught exception:', error);
            await cleanup();
        });
    } catch (err) {
        const error = err instanceof Error ? err : new Error(String(err));
        console.error('Failed to start server:', error);
        process.exit(1);
    }
}