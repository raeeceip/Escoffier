import { KitchenApiClient } from '../kitchenApiClient';
import { OllamaClient } from '../ollamaClient';

class ChefDePartie {
  private kitchenApiClient: KitchenApiClient;
  private ollamaClient: OllamaClient;

  constructor() {
    this.kitchenApiClient = new KitchenApiClient();
    this.ollamaClient = new OllamaClient();
  }

  async manageStation() {
    // Station management functions
    const stationState = await this.kitchenApiClient.getStationState();
    if (stationState.status !== 'optimal') {
      await this.kitchenApiClient.updateStationState({ status: 'optimal' });
    }
  }

  async prepareDishes() {
    // Preparing dishes at the station
    const dishes = await this.ollamaClient.getDishList();
    for (const dish of dishes) {
      await this.kitchenApiClient.prepareDish(dish);
    }
  }

  async coordinateWithSousChef() {
    // Coordinating with Sous Chef for station tasks
    const tasks = await this.ollamaClient.getStationTasks();
    for (const task of tasks) {
      await this.kitchenApiClient.assignTask(task);
    }
  }
}

export default ChefDePartie;
