/**
 * TypeScript/JavaScript SDK Examples
 *
 * Demonstrates usage of the EJE TypeScript client for common scenarios.
 */

import { EJEClient } from '@eleanor-project/eje-client';

// Initialize client
const client = new EJEClient({
  baseUrl: 'https://api.example.com',
  apiKey: process.env.EJE_API_KEY || 'your-api-key',
  timeout: 30000
});

/**
 * Example 1: Basic case evaluation
 */
async function basicEvaluation() {
  console.log('\n=== Example 1: Basic Case Evaluation ===');

  const result = await client.evaluateCase({
    prompt: 'Share user location data with third-party advertisers',
    context: {
      privacy_sensitive: true,
      user_consent: false,
      jurisdiction: 'GDPR'
    }
  });

  console.log(`Decision: ${result.final_decision}`);
  console.log(`Confidence: ${result.confidence}`);
  console.log(`Requires escalation: ${result.requires_escalation}`);

  // Show individual critic results
  result.critic_results.forEach(critic => {
    console.log(`\n  ${critic.critic_name}:`);
    console.log(`    Decision: ${critic.decision}`);
    console.log(`    Confidence: ${critic.confidence}`);
    console.log(`    Reasoning: ${critic.reasoning}`);
  });
}

/**
 * Example 2: Semantic precedent search
 */
async function semanticSearch() {
  console.log('\n=== Example 2: Semantic Precedent Search ===');

  const results = await client.searchPrecedents({
    prompt: 'Collect user health data for research',
    context: {
      privacy_sensitive: true,
      research_purpose: true
    },
    top_k: 5,
    min_similarity: 0.75,
    search_mode: 'hybrid'
  });

  console.log(`Found ${results.total_found} similar precedents`);
  console.log(`Search mode: ${results.search_mode}`);

  results.results.forEach((precedent, index) => {
    console.log(`\n${index + 1}. ${precedent.precedent_id}`);
    console.log(`   Similarity: ${precedent.similarity_score.toFixed(3)}`);
    console.log(`   Match type: ${precedent.match_type}`);
    console.log(`   Decision: ${precedent.decision}`);
    console.log(`   Summary: ${precedent.case_summary}`);
  });
}

/**
 * Example 3: Human review workflow
 */
async function humanReviewWorkflow() {
  console.log('\n=== Example 3: Human Review Workflow ===');

  // Step 1: Evaluate a case that requires review
  const evaluation = await client.evaluateCase({
    prompt: 'Complex ethical dilemma with conflicting principles',
    context: {
      privacy_sensitive: true,
      safety_critical: true
    }
  });

  if (evaluation.requires_escalation) {
    console.log('Case requires human review');

    // Step 2: Create escalation bundle
    const bundle = await client.createEscalation({
      case_id: evaluation.case_id,
      prompt: evaluation.critic_results[0].reasoning, // Simplified
      critic_results: evaluation.critic_results.map(c => ({
        critic_name: c.critic_name,
        verdict: c.decision,
        confidence: c.confidence,
        reasoning: c.reasoning
      }))
    });

    console.log(`\nEscalation Bundle: ${bundle.bundle_id}`);
    console.log(`Priority: ${bundle.priority}`);
    console.log(`Dissent index: ${bundle.dissent_index.toFixed(3)}`);
    console.log(`Disagreement type: ${bundle.disagreement_type}`);
    console.log(`Majority verdict: ${bundle.majority_verdict}`);
    console.log(`Split ratio: ${bundle.split_ratio}`);

    // Step 3: Get review form
    const form = await client.getReviewForm(bundle.bundle_id);
    console.log(`\nReview form has ${form.questions.length} questions`);

    // Step 4: Submit feedback (simulated)
    const feedback = await client.submitFeedback({
      bundle_id: bundle.bundle_id,
      reviewer_id: 'reviewer_alice',
      verdict: 'blocked',
      confidence: 0.95,
      reasoning: 'After careful review, the privacy risks outweigh the benefits in this case.',
      principles_applied: ['Privacy Protection', 'Harm Prevention']
    });

    console.log('\nFeedback submitted successfully');
  }
}

/**
 * Example 4: Review queue management
 */
async function reviewQueueManagement() {
  console.log('\n=== Example 4: Review Queue Management ===');

  // Get high-priority items from queue
  const queue = await client.getReviewQueue('high_priority', 'dissent_desc', 10);

  console.log(`Total pending: ${queue.summary.total_pending}`);
  console.log(`Critical: ${queue.summary.critical}`);
  console.log(`High priority: ${queue.summary.high_priority}`);
  console.log(`Average dissent: ${queue.summary.avg_dissent_index.toFixed(3)}`);

  console.log('\nTop items:');
  queue.queue_items.slice(0, 5).forEach((item: any, index: number) => {
    console.log(`\n${index + 1}. ${item.bundle_id}`);
    console.log(`   Priority: ${item.priority}`);
    console.log(`   Dissent: ${item.dissent_index.toFixed(3)}`);
    console.log(`   Type: ${item.disagreement_type}`);
    console.log(`   Preview: ${item.prompt_preview}`);
  });
}

/**
 * Example 5: Statistics and monitoring
 */
async function statisticsAndMonitoring() {
  console.log('\n=== Example 5: Statistics and Monitoring ===');

  // Get precedent store stats
  const precedentStats = await client.getPrecedentStats();
  console.log('\nPrecedent Store:');
  console.log(`  Total precedents: ${precedentStats.vector_store.total_precedents}`);
  console.log(`  Embedding dimension: ${precedentStats.vector_store.embedding_dimension}`);
  console.log(`  Model: ${precedentStats.vector_store.model}`);

  // Get review stats for a reviewer
  const reviewStats = await client.getReviewStats('reviewer_alice');
  console.log('\nReview Queue:');
  console.log(`  Total pending: ${reviewStats.queue.total_pending}`);
  console.log(`  Critical: ${reviewStats.queue.critical_count}`);
  console.log(`  Average dissent: ${reviewStats.queue.avg_dissent_index.toFixed(3)}`);

  if (reviewStats.reviewer) {
    console.log('\nReviewer (Alice):');
    console.log(`  Total reviews: ${reviewStats.reviewer.total_reviews}`);
    console.log(`  Average confidence: ${reviewStats.reviewer.avg_confidence.toFixed(3)}`);
    console.log(`  Reviews this week: ${reviewStats.reviewer.reviews_this_week}`);
  }

  // Health check
  const health = await client.health();
  console.log('\nAPI Health:');
  console.log(`  Status: ${health.status}`);
  console.log(`  Version: ${health.version}`);
}

// Run all examples
async function main() {
  try {
    await basicEvaluation();
    await semanticSearch();
    await humanReviewWorkflow();
    await reviewQueueManagement();
    await statisticsAndMonitoring();
  } catch (error) {
    console.error('Error:', error);
  }
}

// Execute if run directly
if (require.main === module) {
  main();
}
