"""
Type definitions for Escoffier kitchen simulation
"""
from enum import Enum


class AgentType(Enum):
    """Types of kitchen agents"""
    HEAD_CHEF = "head_chef"
    SOUS_CHEF = "sous_chef"
    LINE_COOK = "line_cook"
    PREP_COOK = "prep_cook"
    PASTRY_CHEF = "pastry_chef"
    GRILL_COOK = "grill_cook"
    SALAD_CHEF = "salad_chef"
    EXPEDITER = "expediter"
    DISHWASHER = "dishwasher"
    KITCHEN_MANAGER = "kitchen_manager"
    FOOD_RUNNER = "food_runner"
    BAKER = "baker"
    BUTCHER = "butcher"
    GARDE_MANGER = "garde_manger"
    SAUCE_CHEF = "sauce_chef"


class AgentStatus(Enum):
    """Agent status states"""
    IDLE = "idle"
    BUSY = "busy"
    COLLABORATING = "collaborating"
    UNAVAILABLE = "unavailable"


class TaskType(Enum):
    """Types of tasks"""
    PREP = "prep"
    COOK = "cook"
    PLATE = "plate"
    CLEAN = "clean"
    SETUP = "setup"
    COLLABORATE = "collaborate"
    DELEGATE = "delegate"
    QUALITY_CHECK = "quality_check"
    INVENTORY = "inventory"
    ORDER = "order"
    SERVE = "serve"
    EXPEDITE = "expedite"
    GARNISH = "garnish"
    SAUCE = "sauce"
    GRILL = "grill"
    BAKE = "bake"
    FRY = "fry"
    ROAST = "roast"
    BRAISE = "braise"
    SAUTE = "saute"
    BLANCH = "blanch"
    SEASON = "season"
    TASTE = "taste"
    TEMPERATURE_CHECK = "temperature_check"
    SANITATION = "sanitation"
    MISE_EN_PLACE = "mise_en_place"


class TaskStatus(Enum):
    """Task status states"""
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ActionType(Enum):
    """Types of actions agents can perform"""
    COOK = "cook"
    PREP = "prep"
    MOVE = "move"
    GET_INGREDIENT = "get_ingredient"
    USE_EQUIPMENT = "use_equipment"
    CLEAN = "clean"
    COMMUNICATE = "communicate"
    COLLABORATE = "collaborate"
    DELEGATE = "delegate"
    QUALITY_CHECK = "quality_check"
    PLATE = "plate"
    SERVE = "serve"


class ScenarioType(Enum):
    """Types of scenarios"""
    COOKING_CHALLENGE = "cooking_challenge"
    COOKING_COMPETITION = "cooking_competition"
    SERVICE_RUSH = "service_rush"
    EQUIPMENT_FAILURE = "equipment_failure"
    TIME_PRESSURE = "time_pressure"
    COLLABORATION_TEST = "collaboration_test"
    SKILL_ASSESSMENT = "skill_assessment"
    CRISIS_MANAGEMENT = "crisis_management"
    RECIPE_DEVELOPMENT = "recipe_development"
    MENU_PLANNING = "menu_planning"
    INVENTORY_MANAGEMENT = "inventory_management"
    QUALITY_CONTROL = "quality_control"
    TRAINING_SESSION = "training_session"
    CATERING_EVENT = "catering_event"
    RESTAURANT_OPENING = "restaurant_opening"
    FOOD_SAFETY_DRILL = "food_safety_drill"
    SEASONAL_MENU = "seasonal_menu"
    DIETARY_RESTRICTIONS = "dietary_restrictions"
    COST_OPTIMIZATION = "cost_optimization"
    CUSTOMER_COMPLAINTS = "customer_complaints"


class ScenarioStatus(Enum):
    """Scenario execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DifficultyLevel(Enum):
    """Recipe difficulty levels"""
    BEGINNER = "beginner"
    EASY = "easy"
    MEDIUM = "medium"
    INTERMEDIATE = "intermediate"
    HARD = "hard"
    EXPERT = "expert"
    MASTER = "master"


class RecipeType(Enum):
    """Types of recipes"""
    APPETIZER = "appetizer"
    MAIN_COURSE = "main_course"
    DESSERT = "dessert"
    SIDE_DISH = "side_dish"
    SOUP = "soup"
    SALAD = "salad"
    BEVERAGE = "beverage"


class CuisineType(Enum):
    """Types of cuisine"""
    ITALIAN = "italian"
    FRENCH = "french"
    CHINESE = "chinese"
    JAPANESE = "japanese"
    INDIAN = "indian"
    MEXICAN = "mexican"
    AMERICAN = "american"
    MEDITERRANEAN = "mediterranean"
    THAI = "thai"
    KOREAN = "korean"
    SPANISH = "spanish"
    GERMAN = "german"
    INTERNATIONAL = "international"


class EquipmentType(Enum):
    """Types of kitchen equipment"""
    STOVE = "stove"
    OVEN = "oven"
    GRILL = "grill"
    FRYER = "fryer"
    MIXER = "mixer"
    BLENDER = "blender"
    FOOD_PROCESSOR = "food_processor"
    REFRIGERATOR = "refrigerator"
    FREEZER = "freezer"
    DISHWASHER = "dishwasher"
    PREP_TABLE = "prep_table"
    CUTTING_BOARD = "cutting_board"
    SCALE = "scale"
    THERMOMETER = "thermometer"


class EquipmentStatus(Enum):
    """Equipment status states"""
    AVAILABLE = "available"
    IN_USE = "in_use"
    MAINTENANCE = "maintenance"
    BROKEN = "broken"


class StationType(Enum):
    """Types of kitchen stations"""
    PREP = "prep"
    HOT = "hot"
    COLD = "cold"
    GRILL = "grill"
    SAUTE = "saute"
    BAKING = "baking"
    PASTRY = "pastry"
    PLATING = "plating"
    WASHING = "washing"


class IngredientCategory(Enum):
    """Categories of ingredients"""
    PROTEIN = "protein"
    VEGETABLE = "vegetable"
    FRUIT = "fruit"
    GRAIN = "grain"
    DAIRY = "dairy"
    SPICE = "spice"
    HERB = "herb"
    OIL = "oil"
    CONDIMENT = "condiment"
    BEVERAGE = "beverage"


class CommunicationType(Enum):
    """Types of communication between agents"""
    DIRECT = "direct"
    BROADCAST = "broadcast"
    EMERGENCY = "emergency"
    STATUS_UPDATE = "status_update"
    REQUEST = "request"
    RESPONSE = "response"


class CrisisType(Enum):
    """Types of crisis events"""
    EQUIPMENT_FAILURE = "equipment_failure"
    INGREDIENT_SHORTAGE = "ingredient_shortage"
    TIME_PRESSURE = "time_pressure"
    STAFF_UNAVAILABLE = "staff_unavailable"
    QUALITY_ISSUE = "quality_issue"
    CUSTOMER_COMPLAINT = "customer_complaint"
    FIRE_HAZARD = "fire_hazard"
    POWER_OUTAGE = "power_outage"