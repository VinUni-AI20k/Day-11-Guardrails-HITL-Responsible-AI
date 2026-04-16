"""
Lab 11 — Part 4: Human-in-the-Loop Design
  TODO 12: Confidence Router
  TODO 13: Design 3 HITL decision points
"""
from dataclasses import dataclass


# ============================================================
# TODO 12: Implement ConfidenceRouter
#
# Route agent responses based on confidence scores:
#   - HIGH (>= 0.9): Auto-send to user
#   - MEDIUM (0.7 - 0.9): Queue for human review
#   - LOW (< 0.7): Escalate to human immediately
#
# Special case: if the action is HIGH_RISK (e.g., money transfer,
# account deletion), ALWAYS escalate regardless of confidence.
#
# Implement the route() method.
# ============================================================

HIGH_RISK_ACTIONS = [
    "transfer_money",
    "close_account",
    "change_password",
    "delete_data",
    "update_personal_info",
]


@dataclass
class RoutingDecision:
    """Result of the confidence router."""
    action: str          # "auto_send", "queue_review", "escalate"
    confidence: float
    reason: str
    priority: str        # "low", "normal", "high"
    requires_human: bool


class ConfidenceRouter:
    """Route agent responses based on confidence and risk level.

    Thresholds:
        HIGH:   confidence >= 0.9 -> auto-send
        MEDIUM: 0.7 <= confidence < 0.9 -> queue for review
        LOW:    confidence < 0.7 -> escalate to human

    High-risk actions always escalate regardless of confidence.
    """

    HIGH_THRESHOLD = 0.9
    MEDIUM_THRESHOLD = 0.7

    def route(self, response: str, confidence: float,
              action_type: str = "general") -> RoutingDecision:
        """Route a response based on confidence score and action type.

        Args:
            response: The agent's response text
            confidence: Confidence score between 0.0 and 1.0
            action_type: Type of action (e.g., "general", "transfer_money")

        Returns:
            RoutingDecision with routing action and metadata
        """
        # Step 1: Check if the action is high-risk (always escalate)
        # Why: High-risk actions like money transfers and account closures can cause
        # irreversible harm. No matter how confident the AI is, a human must approve.
        if action_type in HIGH_RISK_ACTIONS:
            return RoutingDecision(
                action="escalate",
                confidence=confidence,
                reason=f"High-risk action: {action_type}",
                priority="high",
                requires_human=True,
            )

        # Step 2: Route based on confidence thresholds
        if confidence >= self.HIGH_THRESHOLD:
            # HIGH confidence (≥ 0.9): AI is very sure — auto-send to user
            # Why: For routine queries (balance check, FAQ), speed matters more than review.
            return RoutingDecision(
                action="auto_send",
                confidence=confidence,
                reason="High confidence",
                priority="low",
                requires_human=False,
            )
        elif confidence >= self.MEDIUM_THRESHOLD:
            # MEDIUM confidence (0.7–0.9): AI is somewhat sure — queue for human review
            # Why: Responses might be correct but could contain subtle errors.
            # A human reviewer checks before sending, preventing bad experiences.
            return RoutingDecision(
                action="queue_review",
                confidence=confidence,
                reason="Medium confidence — needs review",
                priority="normal",
                requires_human=True,
            )
        else:
            # LOW confidence (< 0.7): AI is uncertain — escalate immediately
            # Why: Low confidence means the AI might produce incorrect or harmful output.
            # A human agent should handle this directly to protect the customer.
            return RoutingDecision(
                action="escalate",
                confidence=confidence,
                reason="Low confidence — escalating to human agent",
                priority="high",
                requires_human=True,
            )


# ============================================================
# TODO 13: Design 3 HITL decision points
#
# For each decision point, define:
# - trigger: What condition activates this HITL check?
# - hitl_model: Which model? (human-in-the-loop, human-on-the-loop,
#   human-as-tiebreaker)
# - context_needed: What info does the human reviewer need?
# - example: A concrete scenario
#
# Think about real banking scenarios where human judgment is critical.
# ============================================================

hitl_decision_points = [
    {
        "id": 1,
        "name": "Large Transaction Approval",
        "trigger": "Customer requests a money transfer exceeding 50,000,000 VND "
                  "or an international wire transfer to a new recipient.",
        "hitl_model": "human-in-the-loop",
        "context_needed": "Transaction amount, sender/receiver account details, "
                         "transaction history with this recipient, customer's typical "
                         "transaction patterns, and any fraud risk score.",
        "example": "A customer asks to wire 200,000,000 VND to a new overseas account. "
                  "The AI prepares the transfer details but pauses execution. A human "
                  "reviewer checks the transaction against fraud patterns and the customer's "
                  "profile before approving or rejecting.",
    },
    {
        "id": 2,
        "name": "Complaint Escalation & Sensitive Topics",
        "trigger": "Customer expresses strong dissatisfaction (negative sentiment score > 0.8), "
                  "mentions legal action, or discusses sensitive topics like discrimination "
                  "or bereavement-related account changes.",
        "hitl_model": "human-as-tiebreaker",
        "context_needed": "Full conversation history, customer sentiment scores, "
                         "customer tier (VIP/regular), previous complaint records, "
                         "and the AI's proposed response.",
        "example": "A customer says 'I will sue VinBank if this isn't resolved today!' "
                  "The AI drafts a de-escalation response, but both the AI and a secondary "
                  "model disagree on the best approach. A human manager reviews both options "
                  "and picks the appropriate response.",
    },
    {
        "id": 3,
        "name": "Suspicious Activity Reporting",
        "trigger": "The system detects potential money laundering patterns: multiple "
                  "small transfers just below reporting thresholds, rapid account "
                  "openings/closings, or transactions matching sanctioned entities.",
        "hitl_model": "human-on-the-loop",
        "context_needed": "Flagged transaction list, pattern analysis report, "
                         "customer KYC data, related accounts network graph, "
                         "and regulatory reporting requirements.",
        "example": "The AI detects 15 transfers of 9,900,000 VND each (just below the "
                  "10,000,000 VND reporting threshold) from one account in 24 hours. "
                  "The AI automatically files a preliminary alert, and a compliance "
                  "officer reviews the case and decides whether to file a Suspicious "
                  "Activity Report (SAR) with the State Bank of Vietnam.",
    },
]


# ============================================================
# Quick tests
# ============================================================

def test_confidence_router():
    """Test ConfidenceRouter with sample scenarios."""
    router = ConfidenceRouter()

    test_cases = [
        ("Balance inquiry", 0.95, "general"),
        ("Interest rate question", 0.82, "general"),
        ("Ambiguous request", 0.55, "general"),
        ("Transfer $50,000", 0.98, "transfer_money"),
        ("Close my account", 0.91, "close_account"),
    ]

    print("Testing ConfidenceRouter:")
    print("=" * 80)
    print(f"{'Scenario':<25} {'Conf':<6} {'Action Type':<18} {'Decision':<15} {'Priority':<10} {'Human?'}")
    print("-" * 80)

    for scenario, conf, action_type in test_cases:
        decision = router.route(scenario, conf, action_type)
        print(
            f"{scenario:<25} {conf:<6.2f} {action_type:<18} "
            f"{decision.action:<15} {decision.priority:<10} "
            f"{'Yes' if decision.requires_human else 'No'}"
        )

    print("=" * 80)


def test_hitl_points():
    """Display HITL decision points."""
    print("\nHITL Decision Points:")
    print("=" * 60)
    for point in hitl_decision_points:
        print(f"\n  Decision Point #{point['id']}: {point['name']}")
        print(f"    Trigger:  {point['trigger']}")
        print(f"    Model:    {point['hitl_model']}")
        print(f"    Context:  {point['context_needed']}")
        print(f"    Example:  {point['example']}")
    print("\n" + "=" * 60)


if __name__ == "__main__":
    test_confidence_router()
    test_hitl_points()
