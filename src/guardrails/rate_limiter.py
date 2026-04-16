import time
from collections import defaultdict, deque

from google.adk.plugins import base_plugin
from google.genai import types

class RateLimitPlugin(base_plugin.BasePlugin):
    """
    Rate Limit Plugin: Restricts users to a maximum number of requests in a given time window.
    
    Why it's needed: Prevent abuse such as spamming requests (DDoS) or brute-forcing 
    prompt injections. Without this, the system is vulnerable to API quota exhaustion and heavy billing.
    """
    def __init__(self, max_requests=10, window_seconds=60):
        super().__init__(name="rate_limiter")
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.user_windows = defaultdict(deque)

    async def on_user_message_callback(self, invocation_context=None, user_message=None, **kwargs):
        """Check if the user has exceeded their rate limit before processing."""
        # Fix: Extract args if passed as keywords in kwargs
        if invocation_context is None: invocation_context = kwargs.get('invocation_context')
        if user_message is None: user_message = kwargs.get('user_message')

        user_id = invocation_context.user_id if invocation_context and hasattr(invocation_context, 'user_id') else "anonymous_user"
        now = time.time()
        window = self.user_windows[user_id]

        # Remove expired timestamps from the front of the deque
        while window and window[0] < now - self.window_seconds:
            window.popleft()

        # Check if length exceeds max requests
        if len(window) >= self.max_requests:
            return types.Content(
                role="model",
                parts=[types.Part.from_text(text="[BLOCKED] Rate limit exceeded. Please wait before sending more requests.")]
            )

        # Allow request and add timestamp
        window.append(now)
        return None
