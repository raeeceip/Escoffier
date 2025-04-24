import { Router } from 'itty-router';
import { OllamaClient } from './ollamaClient';
import { KitchenApiClient } from './kitchenApiClient';

const router = Router();
const ollamaClient = new OllamaClient();
const kitchenApiClient = new KitchenApiClient();

router.get('/agent/:role', async (request) => {
  const role = request.params.role;
  const agentResponse = await ollamaClient.getAgentResponse(role);
  return new Response(JSON.stringify(agentResponse), { status: 200 });
});

router.post('/agent/action', async (request) => {
  const { role, action } = await request.json();
  const validationResponse = await kitchenApiClient.validateAction(role, action);
  if (validationResponse.valid) {
    const agentResponse = await ollamaClient.performAction(role, action);
    return new Response(JSON.stringify(agentResponse), { status: 200 });
  } else {
    return new Response(JSON.stringify({ error: 'Invalid action' }), { status: 400 });
  }
});

addEventListener('fetch', (event) => {
  event.respondWith(router.handle(event.request));
});
