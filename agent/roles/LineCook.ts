import { KitchenApiClient } from '../kitchenApiClient';
import { OllamaClient } from '../ollamaClient';

class LineCook {
  private kitchenApiClient: KitchenApiClient;
  private ollamaClient: OllamaClient;

  constructor() {
    this.kitchenApiClient = new KitchenApiClient();
    this.ollamaClient = new OllamaClient();
  }

  async executeCookingTask(task: string) {
    // Execution of specific cooking tasks
    const taskDetails = await this.ollamaClient.getTaskDetails(task);
    if (taskDetails.valid) {
      await this.kitchenApiClient.performTask(taskDetails);
    } else {
      throw new Error('Invalid cooking task');
    }
  }

  async prepareIngredients(ingredients: string[]) {
    // Preparing ingredients for cooking
    for (const ingredient of ingredients) {
      const ingredientDetails = await this.kitchenApiClient.getIngredientDetails(ingredient);
      if (ingredientDetails.available) {
        await this.kitchenApiClient.prepareIngredient(ingredientDetails);
      } else {
        throw new Error(`Ingredient ${ingredient} not available`);
      }
    }
  }
}

export default LineCook;
