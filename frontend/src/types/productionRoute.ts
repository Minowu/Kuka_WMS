export interface RouteStep {
  id?: number;
  route_id?: number;
  step_number: number;
  stage_level: number;
  step_name: string;
  allowed_machines: string[];
  is_final_cnc_step: boolean;
  created_at?: string;
}

export interface ItemSummary {
  id: number;
  sku: string;
  name: string;
  standard_quantity_per_cart?: number;
}

export interface ProductionRoute {
  id: number;
  route_code: string;
  route_name: string;
  item_id: number;
  version: number;
  is_active: boolean;
  step_count?: number;
  steps?: RouteStep[];
  item?: ItemSummary;
  created_at?: string;
  updated_at?: string;
}

export interface RouteStepInput {
  step_number: number;
  stage_level: number;
  step_name: string;
  allowed_machines: string[];
  is_final_cnc_step: boolean;
}

export interface ProductionRouteCreate {
  route_code: string;
  route_name: string;
  item_id: number;
  version?: number;
  is_active?: boolean;
  steps: RouteStepInput[];
}

export interface ProductionRouteUpdate {
  route_name?: string;
  version?: number;
  is_active?: boolean;
  steps?: RouteStepInput[];
}

export interface AvailableMachine {
  machine_code: string;
  location_count: number;
  positions: string[];
}
