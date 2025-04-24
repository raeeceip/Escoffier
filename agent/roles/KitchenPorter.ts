import { KitchenApiClient } from '../kitchenApiClient';

class KitchenPorter {
  private kitchenApiClient: KitchenApiClient;

  constructor() {
    this.kitchenApiClient = new KitchenApiClient();
  }

  async performCleaning() {
    const action = {
      role: 'KitchenPorter',
      task: 'cleaning'
    };
    const response = await this.kitchenApiClient.performAction(action);
    return response;
  }

  async performMaintenance() {
    const action = {
      role: 'KitchenPorter',
      task: 'maintenance'
    };
    const response = await this.kitchenApiClient.performAction(action);
    return response;
  }
}

export default KitchenPorter;
