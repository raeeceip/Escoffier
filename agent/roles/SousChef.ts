import { KitchenApiClient } from '../kitchenApiClient';
import { OllamaClient } from '../ollamaClient';

class SousChef {
  private kitchenApiClient: KitchenApiClient;
  private ollamaClient: OllamaClient;

  constructor() {
    this.kitchenApiClient = new KitchenApiClient();
    this.ollamaClient = new OllamaClient();
  }

  async manageOperations() {
    // Operational management of kitchen tasks
    const tasks = await this.ollamaClient.getOperationalTasks();
    for (const task of tasks) {
      await this.kitchenApiClient.assignTask(task);
    }
  }

  async monitorInventory() {
    // Monitoring kitchen inventory
    const inventory = await this.kitchenApiClient.getInventory();
    for (const item of inventory) {
      if (item.quantity < 5) {
        await this.kitchenApiClient.orderItem(item.name, 10);
      }
    }
  }

  async ensureQuality() {
    // Ensuring quality of kitchen output
    const kitchenState = await this.kitchenApiClient.getKitchenState();
    if (kitchenState.status !== 'optimal') {
      await this.kitchenApiClient.updateKitchenState({ status: 'optimal' });
    }
  }
}

export default SousChef;
