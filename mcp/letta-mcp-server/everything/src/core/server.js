#!/usr/bin/env node
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { McpError, ErrorCode } from '@modelcontextprotocol/sdk/types.js';
import axios from 'axios';

/**
 * Core LettaServer class that handles initialization and API communication
 */
export class LettaServer {
    /**
     * Initialize the Letta MCP server
     */
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

    /**
     * Get standard headers for API requests
     * @returns {Object} Headers object
     */
    getApiHeaders() {
        return {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-BARE-PASSWORD': `password ${this.password}`,
            'Authorization': `Bearer ${this.password}`
        };
    }

    /**
     * Create a standard error response
     * @param {Error} error - The error object
     * @returns {Object} Formatted error response
     */
    createErrorResponse(error) {
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