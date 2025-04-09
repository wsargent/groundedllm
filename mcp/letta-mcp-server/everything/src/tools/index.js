import { handleListAgents, listAgentsToolDefinition } from './list-agents.js';
import { handlePromptAgent, promptAgentToolDefinition } from './prompt-agent.js';
import { handleListAgentTools, listAgentToolsDefinition } from './list-agent-tools.js';
import { handleListTools, listToolsDefinition } from './list-tools.js';
import { handleCreateAgent, createAgentToolDefinition } from './create-agent.js';
import { handleAttachTool, attachToolToolDefinition } from './attach-tool.js';
import { handleListMemoryBlocks, listMemoryBlocksToolDefinition } from './list-memory-blocks.js';
import { handleReadMemoryBlock, readMemoryBlockToolDefinition } from './read-memory-block.js';
import { handleUpdateMemoryBlock, updateMemoryBlockToolDefinition } from './update-memory-block.js';
import { handleAttachMemoryBlock, attachMemoryBlockToolDefinition } from './attach-memory-block.js';
import { handleCreateMemoryBlock, createMemoryBlockToolDefinition } from './create-memory-block.js';
import { handleUploadTool, uploadToolToolDefinition } from './upload-tool.js';
import { CallToolRequestSchema, ListToolsRequestSchema, McpError, ErrorCode } from '@modelcontextprotocol/sdk/types.js';

/**
 * Register all tool handlers with the server
 * @param {Object} server - The LettaServer instance
 */
export function registerToolHandlers(server) {
    // Register tool definitions
    server.server.setRequestHandler(ListToolsRequestSchema, async () => ({
        tools: [
            listAgentsToolDefinition,
            promptAgentToolDefinition,
            listAgentToolsDefinition,
            listToolsDefinition,
            createAgentToolDefinition,
            attachToolToolDefinition,
            listMemoryBlocksToolDefinition,
            readMemoryBlockToolDefinition,
            updateMemoryBlockToolDefinition,
            attachMemoryBlockToolDefinition,
            createMemoryBlockToolDefinition,
            uploadToolToolDefinition,
        ],
    }));

    // Register tool call handler
    server.server.setRequestHandler(CallToolRequestSchema, async (request) => {
        switch (request.params.name) {
            case 'list_agents':
                return handleListAgents(server, request.params.arguments);
            case 'prompt_agent':
                return handlePromptAgent(server, request.params.arguments);
            case 'list_agent_tools':
                return handleListAgentTools(server, request.params.arguments);
            case 'list_tools':
                return handleListTools(server, request.params.arguments);
            case 'create_agent':
                return handleCreateAgent(server, request.params.arguments);
            case 'attach_tool':
                return handleAttachTool(server, request.params.arguments);
            case 'list_memory_blocks':
                return handleListMemoryBlocks(server, request.params.arguments);
            case 'read_memory_block':
                return handleReadMemoryBlock(server, request.params.arguments);
            case 'update_memory_block':
                return handleUpdateMemoryBlock(server, request.params.arguments);
            case 'attach_memory_block':
                return handleAttachMemoryBlock(server, request.params.arguments);
            case 'create_memory_block':
                return handleCreateMemoryBlock(server, request.params.arguments);
            case 'upload_tool':
                return handleUploadTool(server, request.params.arguments);
            default:
                throw new McpError(
                    ErrorCode.MethodNotFound,
                    `Unknown tool: ${request.params.name}`
                );
        }
    });
}

// Export all tool definitions
export const toolDefinitions = [
    listAgentsToolDefinition,
    promptAgentToolDefinition,
    listAgentToolsDefinition,
    listToolsDefinition,
    createAgentToolDefinition,
    attachToolToolDefinition,
    listMemoryBlocksToolDefinition,
    readMemoryBlockToolDefinition,
    updateMemoryBlockToolDefinition,
    attachMemoryBlockToolDefinition,
    createMemoryBlockToolDefinition,
    uploadToolToolDefinition,
];

// Export all tool handlers
export const toolHandlers = {
    handleListAgents,
    handlePromptAgent,
    handleListAgentTools,
    handleListTools,
    handleCreateAgent,
    handleAttachTool,
    handleListMemoryBlocks,
    handleReadMemoryBlock,
    handleUpdateMemoryBlock,
    handleAttachMemoryBlock,
    handleCreateMemoryBlock,
    handleUploadTool,
};