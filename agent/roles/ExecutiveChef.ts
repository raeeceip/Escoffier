import { KitchenApiClient } from '../kitchenApiClient';
import { OllamaClient } from '../ollamaClient';

class ExecutiveChef {
  private kitchenApiClient: KitchenApiClient;
  private ollamaClient: OllamaClient;

  constructor() {
    this.kitchenApiClient = new KitchenApiClient();
    this.ollamaClient = new OllamaClient();
  }

  async planMenu() {
    // Strategic planning for menu
    const menu = await this.ollamaClient.getMenuSuggestions();
    return menu;
  }

  async overseeOperations() {
    // Oversight of kitchen operations
    const kitchenState = await this.kitchenApiClient.getKitchenState();
    if (kitchenState.status !== 'optimal') {
      await this.kitchenApiClient.updateKitchenState({ status: 'optimal' });
    }
  }

  async delegateTasks() {
    // Delegating tasks to other roles
    const tasks = await this.ollamaClient.getTaskList();
    for (const task of tasks) {
      await this.kitchenApiClient.assignTask(task);
    }
  }
}

export default ExecutiveChef;
