import type { 
  Complaint, Case, GraphNode, GraphLink, 
  ScoredTransaction, ModelMetric 
} from '../types';

export const API_BASE = "http://localhost:8000";

interface AuthResponse {
  access_token: string;
  token_type: string;
  username: string;
}

export const api = {
  // Authentication
  async login(user: string, pass: string): Promise<AuthResponse> {
    const loginData = new URLSearchParams();
    loginData.append('username', user);
    loginData.append('password', pass);

    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: loginData
    });
    if (!res.ok) throw new Error("Authentication failed");
    return res.json();
  },

  // Citizen Complaint submission
  async submitComplaint(data: {
    reporter_name?: string;
    phone?: string | null;
    text_content: string;
    location_lat?: number;
    location_lng?: number;
  }): Promise<Complaint> {
    const res = await fetch(`${API_BASE}/complaints`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        reporter_name: data.reporter_name || "Anonymous",
        phone: data.phone || null,
        text_content: data.text_content,
        location_lat: data.location_lat,
        location_lng: data.location_lng
      })
    });
    if (!res.ok) throw new Error("Submission failed");
    return res.json();
  },

  // Get single complaint details
  async getComplaint(id: number): Promise<Complaint> {
    const res = await fetch(`${API_BASE}/complaints/${id}`);
    if (!res.ok) throw new Error(`Failed to fetch complaint ${id}`);
    return res.json();
  },

  // Check risk / AI Scoring explanation (triggers scorer in orchestrator)
  async checkRisk(id: number): Promise<void> {
    const res = await fetch(`${API_BASE}/complaints/${id}/risk-check`, {
      method: 'POST'
    });
    if (!res.ok) throw new Error("Scoring failed");
  },

  // Counterfeit note scan (multipart file upload)
  async scanCounterfeit(file: File): Promise<{
    id: number;
    verdict: 'Real' | 'Counterfeit' | string;
    confidence: number;
    features: Record<string, any>;
    created_at: string;
  }> {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${API_BASE}/counterfeit/scan`, {
      method: 'POST',
      body: formData
    });
    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}));
      throw new Error(errorData.detail || "Failed to scan counterfeit note");
    }
    return res.json();
  },

  // Speech deepfake audio check (multipart file upload)
  async checkSpeech(file: File): Promise<{
    verdict: 'Deepfake' | 'Safe' | 'Uncertain';
    confidence: number;
    reason: string;
    features: {
      zero_crossing_rate: number;
      rms_energy: number;
      hf_energy_ratio: number;
      duration_seconds: number;
    };
  }> {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${API_BASE}/speech/check`, {
      method: 'POST',
      body: formData
    });
    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}));
      throw new Error(errorData.detail || "Failed to analyze speech file");
    }
    return res.json();
  },

  // Police Portal data fetches
  async getCases(token: string): Promise<Case[]> {
    const res = await fetch(`${API_BASE}/cases`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (!res.ok) throw new Error("Failed to fetch cases");
    return res.json();
  },

  async getGraphCluster(token: string): Promise<{ nodes: GraphNode[]; links: GraphLink[] }> {
    const res = await fetch(`${API_BASE}/graph/cluster`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (!res.ok) throw new Error("Failed to fetch campaign community clusters");
    return res.json();
  },

  async getGeoHeatmap(token: string): Promise<{ type: string; features: any[] }> {
    const res = await fetch(`${API_BASE}/geo/heatmap`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (!res.ok) throw new Error("Failed to fetch PostGIS geospatial coordinates");
    return res.json();
  },

  async verifyEvidence(evId: number, token: string): Promise<{
    verification: { valid: boolean; reason?: string };
    sha256_hash: string;
  }> {
    const res = await fetch(`${API_BASE}/evidence/${evId}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (!res.ok) throw new Error(`Evidence verification failed for EV-#${evId}`);
    return res.json();
  },

  getExportEvidencePdfUrl(evId: number): string {
    return `${API_BASE}/evidence/${evId}/export`;
  },

  // Bank transactions scoring
  async getTransactionScore(txId: string): Promise<ScoredTransaction> {
    const res = await fetch(`${API_BASE}/transactions/${txId}/score`);
    if (!res.ok) throw new Error(`Failed to score transaction ${txId}`);
    return res.json();
  },

  // Admin Model metrics
  async getModelMetrics(token: string): Promise<ModelMetric[]> {
    const res = await fetch(`${API_BASE}/admin/model-metrics`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (!res.ok) throw new Error("Failed to fetch ML model diagnostics");
    return res.json();
  }
};
