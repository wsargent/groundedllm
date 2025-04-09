#!/usr/bin/env node
import axios from 'axios';
import dotenv from 'dotenv';
import express from 'express';
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { SSEServerTransport } from '@modelcontextprotocol/sdk/server/sse.js';
import { CallToolRequestSchema, ListToolsRequestSchema, McpError, ErrorCode, } from '@modelcontextprotocol/sdk/types.js';

// Load environment variables
dotenv.config();

class LettaServer {
    constructor() {
        // Initialize MCP server
        this.server = new Server({
            name: 'letta-server',
            version: '0.1.0',
        }, {
            capabilities: {
                tools: {},
            },
        });

        // Set up error handler
        this.server.onerror = (error) => console.error('[MCP Error]', error);

        // Set up tool handlers
        this.server.setRequestHandler(ListToolsRequestSchema, async () => ({
            tools: [
                {
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
                },
                {
                    name: 'prompt_agent',
                    description: 'Send a message to an agent and get a response',
                    inputSchema: {
                        type: 'object',
                        properties: {
                            agent_id: {
                                type: 'string',
                                description: 'ID of the agent to prompt',
                            },
                            message: {
                                type: 'string',
                                description: 'Message to send to the agent',
                            },
                        },
                        required: ['agent_id', 'message'],
                    },
                },
                {
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
                },
                {
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
                },
            ],
        }));

        // Set up CallTool handler
        this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
            switch (request.params.name) {
                case 'list_agents':
                    return this.handleListAgents(request.params.arguments);
                case 'prompt_agent':
                    return this.handlePromptAgent(request.params.arguments);
                case 'list_agent_tools':
                    return this.handleListAgentTools(request.params.arguments);
                case 'list_tools':
                    return this.handleListTools(request.params.arguments);
                default:
                    throw new McpError(
                        ErrorCode.MethodNotFound,
                        `Unknown tool: ${request.params.name}`
                    );
            }
        });

        // Validate environment variables
        this.apiBase = process.env.LETTA_BASE_URL ?? '';
        this.password = process.env.LETTA_PASSWORD ?? '';
        if (!this.apiBase) {
            throw new Error('Missing required environment variables: LETTA_BASE_URL');
        }

        // Initialize axios instance
        this.apiBase = `${this.apiBase}/v1`;
        this.api = axios.create({
            baseURL: this.apiBase,
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
            },
        });
    }

    async handlePromptAgent(args) {
        try {
            // Validate arguments
            if (!args.agent_id || !args.message) {
                throw new Error('Missing required arguments: agent_id and message');
            }
            // Headers for API requests
            const headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'X-BARE-PASSWORD': `password ${this.password}`,
                'Authorization': `Bearer ${this.password}`
            };
            // First, check if the agent exists
            const agentInfoResponse = await this.api.get(`/agents/${args.agent_id}`, { headers });
            const agentName = agentInfoResponse.data.name;
            // Send message to agent using the messages/stream endpoint
            const response = await this.api.post(`/agents/${args.agent_id}/messages/stream`, {
                messages: [
                    {
                        role: "user",
                        content: args.message
                    }
                ],
                stream_steps: false,
                stream_tokens: false
            }, {
                headers,
                responseType: 'text'
            });
            // Extract the response
            let responseText = "";
            try {
                // The response is in Server-Sent Events (SSE) format
                if (typeof response.data === 'string') {
                    // Find lines that start with "data: "
                    const dataLines = response.data
                        .split('\n')
                        .filter(line => line.trim().startsWith('data: '));
                    // Process each data line
                    const messages = [];
                    for (const line of dataLines) {
                        try {
                            // Extract the JSON part after "data: "
                            const jsonStr = line.substring(6);
                            const eventData = JSON.parse(jsonStr);
                            // Extract the message content based on message type
                            if (eventData.message_type === 'assistant_message' && eventData.content) {
                                // This is the main response message
                                responseText = eventData.content;
                                break;
                            }
                            else if (eventData.message_type === 'reasoning_message' && eventData.reasoning) {
                                // This is the reasoning message (agent's thought process)
                                messages.push(`[Reasoning]: ${eventData.reasoning}`);
                            }
                            else if (eventData.delta && eventData.delta.content) {
                                // This is a streaming delta update
                                messages.push(eventData.delta.content);
                            }
                        }
                        catch (jsonError) {
                            console.error("Error parsing SSE JSON:", jsonError);
                            // If we can't parse the JSON, just add the raw line
                            messages.push(line.substring(6));
                        }
                    }
                    // If we didn't find a specific assistant message, join all messages
                    if (!responseText && messages.length > 0) {
                        responseText = messages.join('\n');
                    }
                    // If we still don't have a response, use the raw data
                    if (!responseText) {
                        responseText = "Received response but couldn't extract message content";
                    }
                }
                else if (response.data) {
                    // Handle non-string response (unlikely with SSE)
                    responseText = JSON.stringify(response.data);
                }
            }
            catch (error) {
                console.error("Error parsing response:", error);
                responseText = "Error parsing agent response";
            }
            return {
                content: [{
                    type: 'text',
                    text: JSON.stringify({
                        success: true,
                        agent_id: args.agent_id,
                        agent_name: agentName,
                        message: args.message,
                        response: responseText,
                        raw_response_length: typeof response.data === 'string' ? response.data.length : JSON.stringify(response.data).length
                    }, null, 2),
                }],
            };
        }
        catch (error) {
            return {
                content: [{
                    type: 'text',
                    text: JSON.stringify({
                        success: false,
                        error: error.message,
                        details: error.response?.data || error,
                    }, null, 2),
                }],
                isError: true,
            };
        }
    }

    async handleListAgents(args) {
        try {
            // Headers for API requests
            const headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'X-BARE-PASSWORD': `password ${this.password}`
            };

            // Get the list of agents
            const response = await this.api.get('/agents', { headers });
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
            return {
                content: [{
                    type: 'text',
                    text: JSON.stringify({
                        success: false,
                        error: error.message,
                        details: error.response?.data || error,
                    }, null, 2),
                }],
                isError: true,
            };
        }
    }

    async handleListAgentTools(args) {
        try {
            if (!args.agent_id) {
                throw new Error('Missing required argument: agent_id');
            }

            const headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'X-BARE-PASSWORD': `password ${this.password}`
            };

            const agentInfoResponse = await this.api.get(`/agents/${args.agent_id}`, { headers });
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
            return {
                content: [{
                    type: 'text',
                    text: JSON.stringify({
                        success: false,
                        error: error.message,
                        details: error.response?.data || error,
                    }, null, 2),
                }],
                isError: true,
            };
        }
    }

    async handleListTools(args) {
        try {
            const headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'X-BARE-PASSWORD': `password ${this.password}`
            };

            const response = await this.api.get('/tools', { headers });
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
            return {
                content: [{
                    type: 'text',
                    text: JSON.stringify({
                        success: false,
                        error: error.message,
                        details: error.response?.data || error,
                    }, null, 2),
                }],
                isError: true,
            };
        }
    }

    async runStdio() {
        try {
            const transport = new StdioServerTransport();
            await this.server.connect(transport);
            console.error('Letta MCP server running on stdio');

            const cleanup = async () => {
                await this.server.close();
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

    async runSSE() {
        try {
            const app = express();
            let transport;
            
            app.get('/sse', async (req, res) => {
                console.log('Received SSE connection');
                transport = new SSEServerTransport('/message', res);
                await this.server.connect(transport);
                
                req.on('close', () => {
                    console.log('SSE connection closed');
                });
                
                this.server.onclose = async () => {
                    console.log('Server closing...');
                    await this.server.close();
                };
            });
            
            app.post('/message', async (req, res) => {
                try {
                    console.log('Received message');
                    if (!transport) {
                        console.error('No active SSE connection');
                        res.status(503).json({ error: 'No active SSE connection' });
                        return;
                    }
                    await transport.handlePostMessage(req, res);
                } catch (error) {
                    console.error('Error handling message:', error);
                    res.status(500).json({ error: 'Internal server error' });
                }
            });
            
            const PORT = process.env.PORT || 3001;
            app.listen(PORT, () => {
                console.log(`Letta SSE server is running on port ${PORT}`);
                console.log(`API credentials: ${this.apiBase ? 'Available' : 'Not available'}`);
            });
            
            const cleanup = async () => {
                if (this.server) {
                    await this.server.close();
                }
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
            console.error('Failed to start SSE server:', error);
            process.exit(1);
        }
    }
}

const server = new LettaServer();
const useSSE = process.argv.includes('--sse');

if (useSSE) {
    server.runSSE().catch(console.error);
} else {
    server.runStdio().catch(console.error);
}
