import express from 'express';
import { SSEServerTransport } from '@modelcontextprotocol/sdk/server/sse.js';

/**
 * Run the server using SSE transport
 * @param {Object} server - The LettaServer instance
 */
export async function runSSE(server) {
    try {
        const app = express();
        let transport;
        let isConnected = false;
        let reconnectAttempts = 0;
        let lastClientId = null;
        const maxReconnectAttempts = 10;
        const reconnectDelay = 2000; // 2 seconds initial delay
        const activeConnections = new Map(); // Track active connections
        
        // Generate a unique client ID
        const generateClientId = () => {
            return `client_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        };
        
        // Function to handle connection and reconnection
        const connectTransport = async (req, res) => {
            const clientIp = req.headers['x-forwarded-for'] || req.socket.remoteAddress;
            const clientId = generateClientId();
            lastClientId = clientId;
            
            try {
                console.log(`Establishing SSE transport for client ${clientId} (${clientIp})`);
                transport = new SSEServerTransport('/message', res);
                
                // Store connection info
                activeConnections.set(clientId, {
                    transport,
                    ip: clientIp,
                    connectedAt: new Date(),
                    req,
                    res
                });
                
                await server.server.connect(transport);
                isConnected = true;
                reconnectAttempts = 0;
                console.log(`SSE transport connected successfully for client ${clientId}`);
                return { success: true, clientId };
            } catch (error) {
                console.error(`Failed to connect SSE transport for client ${clientId}:`, error);
                activeConnections.delete(clientId);
                isConnected = false;
                return { success: false, clientId };
            }
        };
        
        // Function to handle reconnection with exponential backoff
        const attemptReconnect = async (req, res) => {
            if (reconnectAttempts >= maxReconnectAttempts) {
                console.error(`Maximum reconnection attempts (${maxReconnectAttempts}) reached. Giving up.`);
                return { success: false };
            }
            
            reconnectAttempts++;
            const delay = reconnectDelay * Math.pow(1.5, reconnectAttempts - 1);
            console.log(`Attempting to reconnect (${reconnectAttempts}/${maxReconnectAttempts}) in ${delay}ms...`);
            
            return new Promise(resolve => {
                setTimeout(async () => {
                    try {
                        const result = await connectTransport(req, res);
                        console.log(`Reconnection attempt ${reconnectAttempts} ${result.success ? 'successful' : 'failed'} for client ${result.clientId}`);
                        resolve(result);
                    } catch (error) {
                        console.error(`Reconnection attempt ${reconnectAttempts} failed with error:`, error);
                        resolve({ success: false });
                    }
                }, delay);
            });
        };
        
        // Function to clean up a connection
        const cleanupConnection = async (clientId) => {
            if (activeConnections.has(clientId)) {
                const connection = activeConnections.get(clientId);
                console.log(`Cleaning up connection for client ${clientId}`);
                
                try {
                    // Remove from active connections
                    activeConnections.delete(clientId);
                    
                    // Log connection stats
                    console.log(`Connection stats: ${activeConnections.size} active connections`);
                } catch (error) {
                    console.error(`Error cleaning up connection for client ${clientId}:`, error);
                }
            }
        };
        
        app.get('/sse', async (req, res) => {
            const clientIp = req.headers['x-forwarded-for'] || req.socket.remoteAddress;
            const wasDisconnected = !isConnected && transport !== undefined;
            
            if (wasDisconnected) {
                console.log(`Received SSE connection request from ${clientIp} after previous disconnection`);
                console.log(`Attempting to reconnect (previous connection was lost)`);
            } else {
                console.log(`Received new SSE connection request from ${clientIp}`);
            }
            
            // Set headers for SSE
            res.setHeader('Content-Type', 'text/event-stream');
            res.setHeader('Cache-Control', 'no-cache');
            res.setHeader('Connection', 'keep-alive');
            
            // Connect transport
            const result = await connectTransport(req, res);
            if (!result.success) {
                console.log('Initial connection failed, attempting to reconnect...');
                await attemptReconnect(req, res);
            } else if (wasDisconnected) {
                console.log(`Successfully reconnected after previous disconnection (client ${result.clientId})`);
            }
            
            // Store the client ID for cleanup
            const clientId = result.clientId;
            
            // Send initial ping to confirm connection
            try {
                res.write(': connected\n\n');
            } catch (error) {
                console.error(`Error sending initial ping to client ${clientId}:`, error);
            }
            
            req.on('close', async () => {
                console.log(`SSE connection closed for client ${clientId}`);
                isConnected = false;
                
                // Clean up the connection
                await cleanupConnection(clientId);
                
                // Only attempt to reconnect if the server is still running
                if (server.server && !server.server.closed) {
                    console.log('Connection lost, waiting for new client connection to reconnect...');
                    
                    // We can't use the closed response object for reconnection
                    // Instead, we'll set a flag to indicate we should try to reconnect on the next connection
                    reconnectAttempts = 0; // Reset for next connection attempt
                }
            });
            
            server.server.onclose = async () => {
                console.log('Server closing...');
                isConnected = false;
                await server.server.close();
            };
        });
        
        app.post('/message', async (req, res) => {
            try {
                console.log('Received message');
                if (!transport || !isConnected) {
                    console.error('No active SSE connection');
                    res.status(503).json({ error: 'No active SSE connection' });
                    return;
                }
                await transport.handlePostMessage(req, res);
            } catch (error) {
                console.error('Error handling message:', error);
                
                // If error is related to connection, mark as disconnected
                if (error.message && (
                    error.message.includes('connection') ||
                    error.message.includes('transport') ||
                    error.message.includes('closed')
                )) {
                    isConnected = false;
                    console.log('Connection error detected, marking as disconnected');
                    console.log('Will attempt to reconnect on next client connection');
                    
                    // Reset reconnect attempts for next connection
                    reconnectAttempts = 0;
                    
                    // If we have a last client ID, clean it up
                    if (lastClientId) {
                        await cleanupConnection(lastClientId);
                    }
                }
                
                res.status(500).json({ error: 'Internal server error' });
            }
        });
        
        // Add a health check endpoint
        app.get('/health', (req, res) => {
            res.json({
                status: 'ok',
                connected: isConnected,
                activeConnections: activeConnections.size,
                reconnectAttempts,
                maxReconnectAttempts,
                uptime: process.uptime()
            });
        });
        
        // Set up a ping interval to keep connections alive
        const pingInterval = setInterval(() => {
            if (activeConnections.size > 0) {
                console.log(`Sending ping to ${activeConnections.size} active connections`);
                
                for (const [clientId, connection] of activeConnections.entries()) {
                    try {
                        if (connection.res && !connection.res.finished) {
                            connection.res.write(': ping\n\n');
                        }
                    } catch (error) {
                        console.error(`Error sending ping to client ${clientId}:`, error);
                        isConnected = false;
                        cleanupConnection(clientId);
                    }
                }
            }
        }, 30000); // Send ping every 30 seconds
        
        const PORT = process.env.PORT || 3001;
        const httpServer = app.listen(PORT, () => {
            console.log(`Letta SSE server is running on port ${PORT}`);
            console.log(`API credentials: ${server.apiBase ? 'Available' : 'Not available'}`);
            console.log(`Reconnection enabled: max attempts=${maxReconnectAttempts}, initial delay=${reconnectDelay}ms`);
            console.log(`Connection tracking: enabled with ping interval (30s)`);
        });
        
        const cleanup = async () => {
            console.log('Starting cleanup process...');
            
            // Clear the ping interval
            if (pingInterval) {
                console.log('Clearing ping interval');
                clearInterval(pingInterval);
            }
            
            // Clean up all active connections
            console.log(`Cleaning up ${activeConnections.size} active connections`);
            for (const [clientId, connection] of activeConnections.entries()) {
                try {
                    console.log(`Closing connection for client ${clientId}`);
                    activeConnections.delete(clientId);
                } catch (error) {
                    console.error(`Error cleaning up connection for client ${clientId}:`, error);
                }
            }
            
            // Close the HTTP server
            if (httpServer) {
                console.log('Closing HTTP server...');
                httpServer.close();
            }
            
            // Close the MCP server
            if (server.server) {
                console.log('Closing MCP server...');
                await server.server.close();
            }
            
            console.log('Cleanup complete, exiting process');
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