/**
 * Tool handler for prompting an agent in the Letta system
 */
export async function handlePromptAgent(server, args) {
    try {
        // Validate arguments
        if (!args.agent_id || !args.message) {
            throw new Error('Missing required arguments: agent_id and message');
        }
        
        // Headers for API requests
        const headers = server.getApiHeaders();
        
        // First, check if the agent exists
        const agentInfoResponse = await server.api.get(`/agents/${args.agent_id}`, { headers });
        const agentName = agentInfoResponse.data.name;
        
        // Send message to agent using the messages/stream endpoint
        const response = await server.api.post(`/agents/${args.agent_id}/messages/stream`, {
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
    } catch (error) {
        return server.createErrorResponse(error);
    }
}

/**
 * Tool definition for prompt_agent
 */
export const promptAgentToolDefinition = {
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
};