export interface UserProfile {
  displayName: string;
  calorieGoal: number;
  proteinGoal: number;
  carbsGoal: number;
  fatGoal: number;
  fiberGoal: number;
}

export interface Meal {
  id?: string;
  name: string;
  calories: number;
  protein: number;
  carbs: number;
  fat: number;
  fiber: number;
  timestamp: string;
  type: 'breakfast' | 'lunch' | 'dinner' | 'snack';
}

export interface DailyStats {
  calories: number;
  protein: number;
  carbs: number;
  fat: number;
  fiber: number;
}
