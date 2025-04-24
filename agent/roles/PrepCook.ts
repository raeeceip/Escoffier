import { KitchenApiClient } from '../kitchenApiClient';
import { OllamaClient } from '../ollamaClient';

class PrepCook {
  private kitchenApiClient: KitchenApiClient;
  private ollamaClient: OllamaClient;

  constructor() {
    this.kitchenApiClient = new KitchenApiClient();
    this.ollamaClient = new OllamaClient();
  }

  async prepareIngredients(ingredients: string[]) {
    // Ingredient preparation functions
    for (const ingredient of ingredients) {
      const ingredientDetails = await this.kitchenApiClient.getIngredientDetails(ingredient);
      if (ingredientDetails.available) {
        await this.kitchenApiClient.prepareIngredient(ingredientDetails);
      } else {
        throw new Error(`Ingredient ${ingredient} not available`);
      }
    }
  }

  async assistLineCook() {
    // Assisting Line Cook with ingredient preparation
    const tasks = await this.ollamaClient.getPrepTasks();
    for (const task of tasks) {
      await this.kitchenApiClient.performTask(task);
    }
  }
}

export default PrepCook;
