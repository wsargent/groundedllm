#!/usr/bin/env node
import axios from 'axios';

// Configuration
const LETTA_BASE_URL = 'https://letta2.oculair.ca/v1';
const LETTA_PASSWORD = 'lettaSecurePass123';
const AGENT_ID = 'agent-ce9c436e-cefe-4244-9554-8640d54427c7';

async function testAgentCommunication() {
    try {
        // Headers for API requests
        const headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-BARE-PASSWORD': `password ${LETTA_PASSWORD}`,
            'Authorization': `Bearer ${LETTA_PASSWORD}`,
            'user_id': AGENT_ID
        };

        // First, verify agent exists
        console.log('Checking agent...');
        const agentInfo = await axios.get(`${LETTA_BASE_URL}/agents/${AGENT_ID}`, { headers });
        console.log('Agent found:', agentInfo.data.name);

        // Try using the archival_memory_insert function
        console.log('\nTesting archival_memory_insert function...');
        const response = await axios.post(
            `${LETTA_BASE_URL}/agents/${AGENT_ID}/functions`,
            {
                name: "archival_memory_insert",
                arguments: {
                    content: "Test memory entry created at " + new Date().toISOString(),
                    request_heartbeat: false
                }
            },
            { headers }
        );

        console.log('\nResponse from function call:', JSON.stringify(response.data, null, 2));
    } catch (error) {
        console.error('Error:', error.message);
        if (error.response) {
            console.error('Response data:', JSON.stringify(error.response.data, null, 2));
            console.error('Response status:', error.response.status);
            console.error('Response headers:', JSON.stringify(error.response.headers, null, 2));
        }
    }
}

// Run the test
testAgentCommunication().catch(console.error);