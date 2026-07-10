export interface Alert {
  id: number;
  title: string;
  description: string;
  severity: 'Critical' | 'Medium' | 'Low' | string;
  status: string;
  target_role: string;
  created_at: string;
}

export interface GraphNode {
  id: number;
  type: string;
  value: string;
  value_hash: string;
  risk_score: number;
  cluster_id: number;
  x?: number;
  y?: number;
}

export interface GraphLink {
  source: string;
  target: string;
  relation_type: string;
  weight: number;
}

export interface EvidenceItem {
  id: number;
  complaint_id?: number;
  type: string;
  description: string;
  file_path: string;
  sha256_hash: string;
  previous_hash: string;
  created_at: string;
}

export interface Complaint {
  id: number;
  reporter_name: string | null;
  phone: string | null;
  text_content: string;
  risk_score: number;
  risk_explanation: string | null;
  created_at: string;
  location_lat: number | null;
  location_lng: number | null;
  case_id: number | null;
  evidence_items?: EvidenceItem[];
}

export interface Case {
  id: number;
  title: string;
  status: string;
  severity: string;
  assigned_officer_id: number | null;
  created_at: string;
  complaints: Complaint[];
}

export interface ScoredTransaction {
  transaction_id: string;
  sender_account: string;
  receiver_account: string;
  amount: number;
  risk_score: number;
  explanation: string;
}

export interface ModelMetric {
  model_name: string;
  precision: number | null;
  recall: number | null;
  false_positive_rate: number | null;
  status: string;
}
