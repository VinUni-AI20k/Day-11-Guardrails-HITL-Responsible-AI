from google.adk.plugins import base_plugin
from google.genai import types

class ToxicityFilterPlugin(base_plugin.BasePlugin):
    """
    Bonus: 6th Safety Layer - Toxicity Filter
    Blocks highly toxic or hostile inputs immediately before they reach the model.
    """
    def __init__(self):
        super().__init__(name="toxicity_filter")
        # List of extreme toxic words/phrases (mock list for demonstration)
        self.toxic_words = ["stupid", "idiot", "kill", "die", "moron", "hate", "ngu ngoc", "chet"]

    async def on_user_message_callback(self, invocation_context=None, user_message=None, **kwargs):
        if invocation_context is None: invocation_context = kwargs.get('invocation_context')
        if user_message is None: user_message = kwargs.get('user_message')
        text = ""
        if hasattr(user_message, "content"):
            parts = user_message.content.parts
        elif hasattr(user_message, "parts"):
            parts = user_message.parts
        else:
            return None

        for p in parts:
            if hasattr(p, "text") and p.text:
                text += p.text.lower()
        
        for bad_word in self.toxic_words:
            if bad_word in text:
                return types.Content(
                    role="model",
                    parts=[types.Part.from_text(text="[BLOCKED_TOXICITY] Your request contains toxic language and cannot be processed.")]
                )
        return None
