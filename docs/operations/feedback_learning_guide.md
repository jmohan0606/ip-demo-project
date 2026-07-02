# Feedback Learning Guide

## Purpose

Feedback Learning connects:

```text
Recommendation
  -> User Action
  -> Outcome
  -> Learning Signal
  -> Context Memory
  -> Future Recommendations
```

## Actions

- Accept
- Reject
- Ignore
- Complete
- Modify

## Outcomes

- Revenue Impact
- NNM Impact
- AUM Impact
- Meeting Scheduled
- Client Engaged
- Product Review Completed
- No Impact

## UI

Open:

```text
Feedback Learning
```

Steps:

1. Generate sample recommendations if needed
2. Select recommendation
3. Select actor
4. Choose action
5. Add outcome
6. Submit feedback
7. Review learning signals

## API

```text
POST /feedback-learning/submit
POST /feedback-learning/search
GET  /feedback-learning/learning-signals
GET  /feedback-learning/counts
```
