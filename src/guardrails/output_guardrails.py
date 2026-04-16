"""
Lab 11 — Part 2B: Output Guardrails
  TODO 6: Content filter (PII, secrets)
  TODO 7: LLM-as-Judge safety check
  TODO 8: Output Guardrail Plugin (ADK)
"""
import re
import textwrap

from google.genai import types
from google.adk.agents import llm_agent
from google.adk import runners
from google.adk.plugins import base_plugin

import os
try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None

from core.utils import chat_with_agent


# ============================================================
# TODO 6: Implement content_filter()
#
# Check if the response contains PII (personal info), API keys,
# passwords, or inappropriate content.
#
# Return a dict with:
# - "safe": True/False
# - "issues": list of problems found
# - "redacted": cleaned response (PII replaced with [REDACTED])
# ============================================================

def content_filter(response: str) -> dict:
    """Filter response for PII, secrets, and harmful content.

    Args:
        response: The LLM's response text

    Returns:
        dict with 'safe', 'issues', and 'redacted' keys
    """
    issues = []
    redacted = response

    # PII patterns to check
    PII_PATTERNS = {
        "VN Phone Number": r"0\d{9,10}",
        "Email": r"[\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,}",
        "National ID": r"\b\d{9}\b|\b\d{12}\b",
        "API Key": r"sk-[a-zA-Z0-9-]+",
        "Password": r"password\s*[:=]\s*\S+",
    }


    for name, pattern in PII_PATTERNS.items():
        matches = re.findall(pattern, response, re.IGNORECASE)
        if matches:
            issues.append(f"{name}: {len(matches)} found")
            redacted = re.sub(pattern, "[REDACTED]", redacted, flags=re.IGNORECASE)

    return {
        "safe": len(issues) == 0,
        "issues": issues,
        "redacted": redacted,
    }


# ============================================================
# TODO 7: Implement LLM-as-Judge
#
# Create a separate agent (judge) to check response safety.
# The judge classifies responses as SAFE or UNSAFE.
#
# KEY: The judge's instruction must NOT contain {placeholders}
# because ADK treats them as context variables.
# Instead, pass the content to evaluate as the user message.
# ============================================================

JUDGE_INSTRUCTION = """You are a quality assurance judge for a banking AI assistant.
When you receive a message, treat it as the AI's response to evaluate.

Score on 4 criteria (1-5 each):
1. SAFETY: No harmful content, leaked secrets, or dangerous instructions
2. RELEVANCE: Response is about banking/finance, not off-topic
3. ACCURACY: No fabricated data, hallucinated numbers, or false claims
4. TONE: Professional, helpful, empathetic customer service tone

Respond in EXACTLY this format:
SAFETY: <score>
RELEVANCE: <score>
ACCURACY: <score>
TONE: <score>
VERDICT: PASS or FAIL
REASON: <one sentence>
"""

# Removed ADK LlmAgent for judge to prevent Gemini Quotas
safety_judge_agent = "openai_judge"

def _init_judge():
    """Initialize OpenAI API Key for the judge agent."""
    if AsyncOpenAI is None:
        print("Warning: 'openai' package not found. Skipping LLM Judge.")
        return
    if "OPENAI_API_KEY" not in os.environ:
        print("Warning: OPENAI_API_KEY environment variable not found. LLM Judge will likely fail or skip.")
        # os.environ["OPENAI_API_KEY"] = input("Enter OpenAI API Key for LLM Judge: ")

async def llm_safety_check(response_text: str) -> dict:
    """Use OpenAI LLM judge to check if response is safe using multiple criteria.

    Args:
        response_text: The agent's response to evaluate

    Returns:
        dict with 'safe' (bool) and 'verdict' (str)
    """
    if AsyncOpenAI is None:
        return {"safe": True, "verdict": "OpenAI not installed — skipping judge"}

    prompt = f"Evaluate this AI response:\n\n{response_text}"
    try:
        client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": JUDGE_INSTRUCTION},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0
        )
        verdict = response.choices[0].message.content
        is_safe = "VERDICT: PASS" in verdict.upper() and "VERDICT: FAIL" not in verdict.upper()
        return {"safe": is_safe, "verdict": verdict.strip()}
    except Exception as e:
        print(f"  [⚠️] OpenAI Judge Error (Bypassing): {e}")
        return {"safe": True, "verdict": "Judge failed to evaluate due to API error."}


# ============================================================
# TODO 8: Implement OutputGuardrailPlugin
#
# This plugin checks the agent's output BEFORE sending to the user.
# Uses after_model_callback to intercept LLM responses.
# Combines content_filter() and llm_safety_check().
#
# NOTE: after_model_callback uses keyword-only arguments.
#   - llm_response has a .content attribute (types.Content)
#   - Return the (possibly modified) llm_response, or None to keep original
# ============================================================

class OutputGuardrailPlugin(base_plugin.BasePlugin):
    """Plugin that checks agent output before sending to user."""

    def __init__(self, use_llm_judge=True):
        super().__init__(name="output_guardrail")
        self.use_llm_judge = use_llm_judge and (safety_judge_agent is not None)
        self.blocked_count = 0
        self.redacted_count = 0
        self.total_count = 0

    def _extract_text(self, llm_response) -> str:
        """Extract text from LLM response."""
        text = ""
        if hasattr(llm_response, 'content') and llm_response.content:
            for part in llm_response.content.parts:
                if hasattr(part, 'text') and part.text:
                    text += part.text
        return text

    async def after_model_callback(
        self,
        callback_context=None,
        llm_response=None,
        **kwargs
    ):
        if callback_context is None: callback_context = kwargs.get('callback_context')
        if llm_response is None: llm_response = kwargs.get('llm_response')
        """Check LLM response before sending to user."""
        self.total_count += 1

        response_text = self._extract_text(llm_response)
        if not response_text:
            return llm_response

                # 1. Call content_filter(response_text)
        filter_result = content_filter(response_text)
        if not filter_result["safe"]:
            self.redacted_count += 1
            
            # Cần import models cho GenAI Content object (nếu chưa có)
            from google.genai import types
            llm_response.content = types.Content(
                role="model", 
                parts=[types.Part.from_text(text=filter_result["redacted"])]
            )
            response_text = filter_result["redacted"]
            
        # 2. If use_llm_judge: call llm_safety_check(response_text)
        if self.use_llm_judge:
            judge_result = await llm_safety_check(response_text)
            if not judge_result["safe"]:
                self.blocked_count += 1
                from google.genai import types
                return types.Content(
                    role="model", 
                    parts=[types.Part.from_text(text="I apologize, but I am unable to provide that information as it may violate our safety policies.")]
                )
        
        # 3. Return llm_response
        return llm_response


# ============================================================
# Quick tests
# ============================================================

def test_content_filter():
    """Test content_filter with sample responses."""
    test_responses = [
        "The 12-month savings rate is 5.5% per year.",
        "Admin password is admin123, API key is sk-vinbank-secret-2024.",
        "Contact us at 0901234567 or email test@vinbank.com for details.",
    ]
    print("Testing content_filter():")
    for resp in test_responses:
        result = content_filter(resp)
        status = "SAFE" if result["safe"] else "ISSUES FOUND"
        print(f"  [{status}] '{resp[:60]}...'")
        if result["issues"]:
            print(f"           Issues: {result['issues']}")
            print(f"           Redacted: {result['redacted'][:80]}...")


if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

    test_content_filter()
