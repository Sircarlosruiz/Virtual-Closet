---
bolt: 016-tryoff-job-service
created: 2026-05-31T16:30:00Z
status: accepted
superseded_by: null
---

# ADR-001: Separate Celery Queue for TryOff Jobs

## Context

The Virtual Closet backend currently processes VTON (Virtual Try-On) generation jobs through a single Celery queue (`vton`). These jobs involve calling external AI model services (IDM-VTON, CatVARN) which can take 30-90 seconds to complete. The system now needs to add TryOff (garment extraction) jobs that call a different AI model service (FLUX.1-dev) with similar processing times (60-120 seconds).

**Problem**: If both job types share the same queue, a burst of TryOff jobs could starve VTON jobs (or vice versa), leading to unpredictable processing times and poor user experience. For example, if 50 TryOff jobs are submitted simultaneously, VTON jobs queued behind them would wait 50+ minutes before processing starts.

**Constraints**:
- Both job types have similar resource requirements (HTTP calls to GPU-based AI services)
- Processing times are comparable (30-120 seconds)
- The system must maintain predictable response times for both features
- Celery workers are a finite resource (limited by available compute)

**Forces at play**:
- **Isolation vs. Utilization**: Separate queues provide isolation but may leave workers idle when one queue is empty
- **Predictability vs. Efficiency**: Predictable processing times require resource reservation, which reduces overall throughput
- **Simplicity vs. Flexibility**: A single queue is simpler but doesn't allow per-feature scaling

## Decision

Use a **dedicated Celery queue** named `tryoff` for all TryOff job processing, separate from the existing `vton` queue.

**Implementation**:
- Celery task decorated with `@celery_app.task(queue="tryoff")`
- Celery worker started with `celery -A backend worker -Q tryoff` (dedicated worker)
- Queue configuration in `celeryconfig.py` defines routing rules
- Environment variable `TRYOFF_QUEUE_NAME=tryoff` allows configuration

## Rationale

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| **Shared queue with priority levels** | Single queue is simpler; priority can prevent starvation | Celery priority support is limited (only 4 levels); doesn't prevent long-term starvation if high-priority jobs continuously arrive | Rejected: Insufficient isolation for burst scenarios |
| **Shared queue with concurrency limits** | Single queue; limits prevent one job type from monopolizing workers | Requires complex worker configuration; doesn't guarantee processing times; still vulnerable to queue buildup | Rejected: Too complex, insufficient guarantees |
| **Separate queues (chosen)** | Complete isolation; predictable processing times; independent scaling | Workers may be idle when their queue is empty; requires more compute resources | **Accepted**: Predictability and isolation outweigh resource efficiency concerns |
| **Separate Celery apps** | Maximum isolation; independent configuration | Duplicates infrastructure; harder to share common code; operational complexity | Rejected: Over-engineering for this use case |

### Why Separate Queues Won

1. **Predictable Processing Times**: Users expect consistent response times. A burst of TryOff jobs should not delay VTON jobs by 50+ minutes.

2. **Independent Scaling**: TryOff and VTON workloads may have different patterns (e.g., TryOff might be used more during product photo shoots, VTON during customer browsing). Separate queues allow scaling workers independently based on demand.

3. **Fault Isolation**: If the TryOff model service becomes unavailable, TryOff jobs will fail but VTON jobs continue processing. This improves system resilience.

4. **Monitoring and Debugging**: Separate queues make it easier to monitor queue depth, processing times, and failure rates per feature. This aids in capacity planning and incident response.

5. **Future Flexibility**: If we later add more AI-powered features (e.g., background removal, color correction), the pattern is already established. Each feature gets its own queue.

## Consequences

### Positive

- **Predictable processing times**: TryOff jobs don't delay VTON jobs (and vice versa)
- **Independent scaling**: Can add TryOff workers without affecting VTON capacity
- **Fault isolation**: TryOff service outages don't impact VTON processing
- **Clear monitoring**: Queue metrics (depth, latency, errors) are per-feature
- **Operational clarity**: Easy to identify which feature is experiencing issues

### Negative

- **Resource inefficiency**: TryOff workers may be idle when no TryOff jobs are queued, while VTON workers are busy (or vice versa)
- **Increased infrastructure**: Requires separate worker processes for each queue, consuming more compute resources
- **Operational complexity**: Need to monitor and manage multiple queues and worker pools
- **Capacity planning**: Must provision workers for peak load on each queue independently

### Risks

- **Worker underutilization**: If TryOff adoption is low, dedicated workers may sit idle most of the time.
  - **Mitigation**: Start with 1-2 TryOff workers; scale up based on actual queue depth metrics. Can repurpose workers if needed.
  
- **Queue buildup during outages**: If TryOff model service is down, jobs will accumulate in the queue.
  - **Mitigation**: Implement circuit breaker in `TryoffModelClient`; alert on queue depth > 100; provide admin endpoint to cancel stuck jobs.

- **Misconfiguration**: Developers might forget to specify `queue="tryoff"` on new TryOff tasks, causing them to run on VTON workers.
  - **Mitigation**: Add linting rule to enforce queue specification; document pattern in AGENTS.md; code review checklist.

## Related

- **Stories**: 002-process-job-celery (Celery task implementation)
- **Standards**: Consider adding to `system-architecture.md` under "Async Job Processing" section
- **Previous ADRs**: None (first ADR for this bolt)
