/**
 * Eleanor Judicial Engine (EJE) TypeScript/JavaScript Client
 *
 * Provides a type-safe client for the EJE REST API with support for:
 * - Case evaluation
 * - Precedent search (hash-based and semantic)
 * - Human review workflows
 * - Calibration and drift monitoring
 * - Performance analytics
 *
 * @packageDocumentation
 */

/**
 * Client configuration options
 */
export interface EJEClientConfig {
  /** Base URL of the EJE API (e.g., "https://api.example.com") */
  baseUrl: string;
  /** Bearer token for authentication */
  apiKey?: string;
  /** Request timeout in milliseconds (default: 30000) */
  timeout?: number;
  /** Custom headers to include in all requests */
  headers?: Record<string, string>;
}

/**
 * Case evaluation request
 */
export interface CaseRequest {
  /** Optional case identifier */
  case_id?: string;
  /** Prompt describing the case */
  prompt: string;
  /** Additional context for evaluation */
  context?: Record<string, any>;
  /** Whether to require human review */
  require_human_review?: boolean;
}

/**
 * Individual critic result
 */
export interface CriticResult {
  /** Name of the critic */
  critic_name: string;
  /** Decision: "allowed", "blocked", or "review" */
  decision: string;
  /** Confidence score (0.0 to 1.0) */
  confidence: number;
  /** Explanation for the decision */
  reasoning: string;
  /** Execution time in milliseconds */
  execution_time_ms: number;
}

/**
 * Case evaluation response
 */
export interface DecisionResponse {
  /** Case identifier */
  case_id: string;
  /** Decision status */
  status: string;
  /** Final aggregated decision */
  final_decision: string;
  /** Overall confidence */
  confidence: number;
  /** Results from individual critics */
  critic_results: CriticResult[];
  /** IDs of precedents applied */
  precedents_applied: string[];
  /** Whether the case requires escalation */
  requires_escalation: boolean;
  /** Audit log entry ID */
  audit_log_id: string;
  /** Timestamp of evaluation */
  timestamp: string;
  /** Total execution time in milliseconds */
  execution_time_ms: number;
}

/**
 * Semantic search request
 */
export interface SemanticSearchRequest {
  /** Search prompt */
  prompt: string;
  /** Search context */
  context?: Record<string, any>;
  /** Number of results to return */
  top_k?: number;
  /** Minimum similarity threshold (0.0 to 1.0) */
  min_similarity?: number;
  /** Search mode: "exact", "semantic", or "hybrid" */
  search_mode?: 'exact' | 'semantic' | 'hybrid';
}

/**
 * Semantic precedent result
 */
export interface SemanticPrecedentResult {
  /** Precedent identifier */
  precedent_id: string;
  /** Similarity score (0.0 to 1.0) */
  similarity_score: number;
  /** Match type: "exact", "semantic", or "hybrid" */
  match_type: string;
  /** Case summary */
  case_summary: string;
  /** Decision */
  decision: string;
  /** Reasoning */
  reasoning: string;
  /** Timestamp */
  timestamp: string;
}

/**
 * Semantic search response
 */
export interface SemanticSearchResponse {
  /** Query summary */
  query_summary: string;
  /** Search results */
  results: SemanticPrecedentResult[];
  /** Total number of results found */
  total_found: number;
  /** Search mode used */
  search_mode: string;
  /** Execution time in milliseconds */
  execution_time_ms: number;
}

/**
 * Escalation request
 */
export interface EscalationRequest {
  /** Case identifier */
  case_id: string;
  /** Case prompt */
  prompt: string;
  /** Case context */
  context?: Record<string, any>;
  /** Critic results */
  critic_results: Array<Record<string, any>>;
  /** Optional priority override */
  priority?: string;
}

/**
 * Escalation response
 */
export interface EscalationResponse {
  /** Bundle identifier */
  bundle_id: string;
  /** Case identifier */
  case_id: string;
  /** Priority level */
  priority: string;
  /** Dissent index (0.0 to 1.0) */
  dissent_index: number;
  /** Disagreement type */
  disagreement_type: string;
  /** Majority verdict */
  majority_verdict: string;
  /** Vote split ratio */
  split_ratio: string;
  /** Number of similar precedents found */
  num_similar_precedents: number;
  /** Explanation summary */
  explanation_summary: string;
  /** Creation timestamp */
  created_at: string;
}

/**
 * Feedback submission
 */
export interface FeedbackSubmission {
  /** Bundle identifier */
  bundle_id: string;
  /** Reviewer identifier */
  reviewer_id: string;
  /** Verdict */
  verdict: string;
  /** Confidence (0.0 to 1.0) */
  confidence: number;
  /** Reasoning */
  reasoning: string;
  /** Additional responses */
  responses?: Record<string, any>;
  /** Conditions (for conditional verdicts) */
  conditions?: string;
  /** Principles applied */
  principles_applied?: string[];
}

/**
 * API error response
 */
export class EJEAPIError extends Error {
  constructor(
    message: string,
    public statusCode: number,
    public detail?: any
  ) {
    super(message);
    this.name = 'EJEAPIError';
  }
}

/**
 * Eleanor Judicial Engine API Client
 *
 * @example
 * ```typescript
 * const client = new EJEClient({
 *   baseUrl: 'https://api.example.com',
 *   apiKey: 'your-api-key'
 * });
 *
 * const result = await client.evaluateCase({
 *   prompt: 'Share user location data with third party',
 *   context: { privacy_sensitive: true }
 * });
 *
 * console.log(result.final_decision);
 * ```
 */
export class EJEClient {
  private baseUrl: string;
  private headers: Record<string, string>;
  private timeout: number;

  /**
   * Create new EJE client
   * @param config Client configuration
   */
  constructor(config: EJEClientConfig) {
    this.baseUrl = config.baseUrl.replace(/\/$/, ''); // Remove trailing slash
    this.timeout = config.timeout || 30000;

    this.headers = {
      'Content-Type': 'application/json',
      ...config.headers
    };

    if (config.apiKey) {
      this.headers['Authorization'] = `Bearer ${config.apiKey}`;
    }
  }

  /**
   * Make HTTP request to API
   */
  private async request<T>(
    method: string,
    path: string,
    body?: any
  ): Promise<T> {
    const url = `${this.baseUrl}${path}`;

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      const response = await fetch(url, {
        method,
        headers: this.headers,
        body: body ? JSON.stringify(body) : undefined,
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new EJEAPIError(
          error.detail || `HTTP ${response.status}: ${response.statusText}`,
          response.status,
          error
        );
      }

      return await response.json();
    } catch (error) {
      clearTimeout(timeoutId);

      if (error instanceof EJEAPIError) {
        throw error;
      }

      if (error.name === 'AbortError') {
        throw new EJEAPIError('Request timeout', 408);
      }

      throw new EJEAPIError(
        error.message || 'Network error',
        0,
        error
      );
    }
  }

  /**
   * Evaluate a case
   *
   * @param request Case evaluation request
   * @returns Decision response
   *
   * @example
   * ```typescript
   * const result = await client.evaluateCase({
   *   prompt: 'Access user medical records',
   *   context: { privacy_sensitive: true, jurisdiction: 'GDPR' }
   * });
   * ```
   */
  async evaluateCase(request: CaseRequest): Promise<DecisionResponse> {
    return this.request<DecisionResponse>('POST', '/evaluate', request);
  }

  /**
   * Search for semantically similar precedents
   *
   * @param request Semantic search request
   * @returns Search results
   *
   * @example
   * ```typescript
   * const results = await client.searchPrecedents({
   *   prompt: 'Share location data',
   *   context: { privacy_sensitive: true },
   *   top_k: 10,
   *   search_mode: 'hybrid'
   * });
   * ```
   */
  async searchPrecedents(
    request: SemanticSearchRequest
  ): Promise<SemanticSearchResponse> {
    return this.request<SemanticSearchResponse>(
      'POST',
      '/precedents/search/semantic',
      request
    );
  }

  /**
   * Find precedents similar to an existing precedent
   *
   * @param precedentId Precedent ID
   * @param topK Number of results (default: 10)
   * @param minSimilarity Minimum similarity (default: 0.75)
   * @returns Similar precedents
   *
   * @example
   * ```typescript
   * const similar = await client.findSimilarPrecedents('prec_123', 5, 0.8);
   * ```
   */
  async findSimilarPrecedents(
    precedentId: string,
    topK: number = 10,
    minSimilarity: number = 0.75
  ): Promise<SemanticSearchResponse> {
    return this.request<SemanticSearchResponse>(
      'GET',
      `/precedents/${precedentId}/similar?top_k=${topK}&min_similarity=${minSimilarity}`,
      undefined
    );
  }

  /**
   * Create escalation bundle for human review
   *
   * @param request Escalation request
   * @returns Escalation bundle
   *
   * @example
   * ```typescript
   * const bundle = await client.createEscalation({
   *   case_id: 'case_123',
   *   prompt: 'Complex ethical dilemma',
   *   context: {},
   *   critic_results: [
   *     { critic_name: 'privacy', verdict: 'blocked', confidence: 0.9, reasoning: '...' },
   *     { critic_name: 'autonomy', verdict: 'allowed', confidence: 0.8, reasoning: '...' }
   *   ]
   * });
   * ```
   */
  async createEscalation(
    request: EscalationRequest
  ): Promise<EscalationResponse> {
    return this.request<EscalationResponse>(
      'POST',
      '/review/escalate',
      request
    );
  }

  /**
   * Get review queue
   *
   * @param filter Filter option
   * @param sortBy Sort option
   * @param limit Maximum items to return
   * @returns Queue summary
   *
   * @example
   * ```typescript
   * const queue = await client.getReviewQueue('high_priority', 'dissent_desc', 20);
   * ```
   */
  async getReviewQueue(
    filter: string = 'all',
    sortBy: string = 'priority_desc',
    limit: number = 50
  ): Promise<any> {
    return this.request<any>('POST', '/review/queue', {
      filter_by: filter,
      sort_by: sortBy,
      limit
    });
  }

  /**
   * Submit review feedback
   *
   * @param feedback Feedback submission
   * @returns Submission confirmation
   *
   * @example
   * ```typescript
   * await client.submitFeedback({
   *   bundle_id: 'bundle_123',
   *   reviewer_id: 'reviewer_alice',
   *   verdict: 'blocked',
   *   confidence: 0.95,
   *   reasoning: 'Clear privacy violation...',
   *   principles_applied: ['Privacy Protection', 'Legal Compliance']
   * });
   * ```
   */
  async submitFeedback(feedback: FeedbackSubmission): Promise<any> {
    return this.request<any>('POST', '/review/submit', feedback);
  }

  /**
   * Get review form for bundle
   *
   * @param bundleId Bundle identifier
   * @returns Feedback form
   *
   * @example
   * ```typescript
   * const form = await client.getReviewForm('bundle_123');
   * console.log(form.questions);
   * ```
   */
  async getReviewForm(bundleId: string): Promise<any> {
    return this.request<any>('GET', `/review/form/${bundleId}`, undefined);
  }

  /**
   * Get review statistics
   *
   * @param reviewerId Optional reviewer ID for personalized stats
   * @returns Statistics
   *
   * @example
   * ```typescript
   * const stats = await client.getReviewStats('reviewer_alice');
   * console.log(stats.queue.total_pending);
   * console.log(stats.reviewer.total_reviews);
   * ```
   */
  async getReviewStats(reviewerId?: string): Promise<any> {
    const query = reviewerId ? `?reviewer_id=${reviewerId}` : '';
    return this.request<any>('GET', `/review/stats${query}`, undefined);
  }

  /**
   * Get precedent store statistics
   *
   * @returns Store statistics
   *
   * @example
   * ```typescript
   * const stats = await client.getPrecedentStats();
   * console.log(stats.vector_store.total_precedents);
   * ```
   */
  async getPrecedentStats(): Promise<any> {
    return this.request<any>('GET', '/precedents/stats', undefined);
  }

  /**
   * Health check
   *
   * @returns Health status
   *
   * @example
   * ```typescript
   * const health = await client.health();
   * console.log(health.status);
   * ```
   */
  async health(): Promise<any> {
    return this.request<any>('GET', '/health', undefined);
  }
}

// Export default
export default EJEClient;
