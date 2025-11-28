"""
Python SDK Examples

Demonstrates usage of the EJE Python client for common scenarios.
"""

import os
from eje_client import EJEClient, AsyncEJEClient
import asyncio


# Initialize client
client = EJEClient(
    base_url=os.getenv('EJE_BASE_URL', 'https://api.example.com'),
    api_key=os.getenv('EJE_API_KEY', 'your-api-key'),
    timeout=30
)


def example_1_basic_evaluation():
    """Example 1: Basic case evaluation."""
    print('\n=== Example 1: Basic Case Evaluation ===')

    result = client.evaluate_case(
        prompt='Share user location data with third-party advertisers',
        context={
            'privacy_sensitive': True,
            'user_consent': False,
            'jurisdiction': 'GDPR'
        }
    )

    print(f"Decision: {result['final_decision']}")
    print(f"Confidence: {result['confidence']}")
    print(f"Requires escalation: {result['requires_escalation']}")

    # Show individual critic results
    for critic in result['critic_results']:
        print(f"\n  {critic['critic_name']}:")
        print(f"    Decision: {critic['decision']}")
        print(f"    Confidence: {critic['confidence']}")
        print(f"    Reasoning: {critic['reasoning']}")


def example_2_semantic_search():
    """Example 2: Semantic precedent search."""
    print('\n=== Example 2: Semantic Precedent Search ===')

    results = client.search_precedents(
        prompt='Collect user health data for research',
        context={
            'privacy_sensitive': True,
            'research_purpose': True
        },
        top_k=5,
        min_similarity=0.75,
        search_mode='hybrid'
    )

    print(f"Found {results['total_found']} similar precedents")
    print(f"Search mode: {results['search_mode']}")

    for i, precedent in enumerate(results['results'], 1):
        print(f"\n{i}. {precedent['precedent_id']}")
        print(f"   Similarity: {precedent['similarity_score']:.3f}")
        print(f"   Match type: {precedent['match_type']}")
        print(f"   Decision: {precedent['decision']}")
        print(f"   Summary: {precedent['case_summary']}")


def example_3_human_review_workflow():
    """Example 3: Human review workflow."""
    print('\n=== Example 3: Human Review Workflow ===')

    # Step 1: Evaluate a case that requires review
    evaluation = client.evaluate_case(
        prompt='Complex ethical dilemma with conflicting principles',
        context={
            'privacy_sensitive': True,
            'safety_critical': True
        }
    )

    if evaluation['requires_escalation']:
        print('Case requires human review')

        # Step 2: Create escalation bundle
        bundle = client.create_escalation(
            case_id=evaluation['case_id'],
            prompt=evaluation['critic_results'][0]['reasoning'],
            critic_results=[
                {
                    'critic_name': c['critic_name'],
                    'verdict': c['decision'],
                    'confidence': c['confidence'],
                    'reasoning': c['reasoning']
                }
                for c in evaluation['critic_results']
            ]
        )

        print(f"\nEscalation Bundle: {bundle['bundle_id']}")
        print(f"Priority: {bundle['priority']}")
        print(f"Dissent index: {bundle['dissent_index']:.3f}")
        print(f"Disagreement type: {bundle['disagreement_type']}")
        print(f"Majority verdict: {bundle['majority_verdict']}")
        print(f"Split ratio: {bundle['split_ratio']}")

        # Step 3: Get review form
        form = client.get_review_form(bundle['bundle_id'])
        print(f"\nReview form has {len(form['questions'])} questions")

        # Step 4: Submit feedback
        feedback = client.submit_feedback(
            bundle_id=bundle['bundle_id'],
            reviewer_id='reviewer_alice',
            verdict='blocked',
            confidence=0.95,
            reasoning='After careful review, the privacy risks outweigh the benefits.',
            principles_applied=['Privacy Protection', 'Harm Prevention']
        )

        print('\nFeedback submitted successfully')


def example_4_review_queue_management():
    """Example 4: Review queue management."""
    print('\n=== Example 4: Review Queue Management ===')

    # Get high-priority items from queue
    queue = client.get_review_queue(
        filter_by='high_priority',
        sort_by='dissent_desc',
        limit=10
    )

    print(f"Total pending: {queue['summary']['total_pending']}")
    print(f"Critical: {queue['summary']['critical']}")
    print(f"High priority: {queue['summary']['high_priority']}")
    print(f"Average dissent: {queue['summary']['avg_dissent_index']:.3f}")

    print('\nTop items:')
    for i, item in enumerate(queue['queue_items'][:5], 1):
        print(f"\n{i}. {item['bundle_id']}")
        print(f"   Priority: {item['priority']}")
        print(f"   Dissent: {item['dissent_index']:.3f}")
        print(f"   Type: {item['disagreement_type']}")
        print(f"   Preview: {item['prompt_preview']}")


def example_5_statistics_and_monitoring():
    """Example 5: Statistics and monitoring."""
    print('\n=== Example 5: Statistics and Monitoring ===')

    # Get precedent store stats
    precedent_stats = client.get_precedent_stats()
    print('\nPrecedent Store:')
    print(f"  Total precedents: {precedent_stats['vector_store']['total_precedents']}")
    print(f"  Embedding dimension: {precedent_stats['vector_store']['embedding_dimension']}")
    print(f"  Model: {precedent_stats['vector_store']['model']}")

    # Get review stats
    review_stats = client.get_review_stats('reviewer_alice')
    print('\nReview Queue:')
    print(f"  Total pending: {review_stats['queue']['total_pending']}")
    print(f"  Critical: {review_stats['queue']['critical_count']}")
    print(f"  Average dissent: {review_stats['queue']['avg_dissent_index']:.3f}")

    if 'reviewer' in review_stats:
        print('\nReviewer (Alice):')
        print(f"  Total reviews: {review_stats['reviewer']['total_reviews']}")
        print(f"  Average confidence: {review_stats['reviewer']['avg_confidence']:.3f}")
        print(f"  Reviews this week: {review_stats['reviewer']['reviews_this_week']}")

    # Health check
    health = client.health()
    print('\nAPI Health:')
    print(f"  Status: {health['status']}")
    print(f"  Version: {health['version']}")


# Async examples
async def async_example_basic():
    """Async example: Basic case evaluation."""
    print('\n=== Async Example: Basic Case Evaluation ===')

    async with AsyncEJEClient(
        base_url=os.getenv('EJE_BASE_URL', 'https://api.example.com'),
        api_key=os.getenv('EJE_API_KEY', 'your-api-key')
    ) as client:
        result = await client.evaluate_case(
            prompt='Share user location data',
            context={'privacy_sensitive': True}
        )

        print(f"Decision: {result['final_decision']}")
        print(f"Confidence: {result['confidence']}")


async def async_example_concurrent():
    """Async example: Concurrent requests."""
    print('\n=== Async Example: Concurrent Requests ===')

    async with AsyncEJEClient(
        base_url=os.getenv('EJE_BASE_URL', 'https://api.example.com'),
        api_key=os.getenv('EJE_API_KEY', 'your-api-key')
    ) as client:
        # Run multiple evaluations concurrently
        tasks = [
            client.evaluate_case(prompt='Case 1', context={}),
            client.evaluate_case(prompt='Case 2', context={}),
            client.evaluate_case(prompt='Case 3', context={})
        ]

        results = await asyncio.gather(*tasks)

        for i, result in enumerate(results, 1):
            print(f"\nCase {i}: {result['final_decision']}")


def main():
    """Run all examples."""
    # Synchronous examples
    example_1_basic_evaluation()
    example_2_semantic_search()
    example_3_human_review_workflow()
    example_4_review_queue_management()
    example_5_statistics_and_monitoring()

    # Async examples
    asyncio.run(async_example_basic())
    asyncio.run(async_example_concurrent())

    # Clean up
    client.close()


if __name__ == '__main__':
    main()
