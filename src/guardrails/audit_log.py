import json
import time
from datetime import datetime
from google.adk.plugins import base_plugin

class AuditLogPlugin(base_plugin.BasePlugin):
    """
    Audit Log Plugin: Records all interactions, including inputs, outputs, and model processing latency.
    
    Why it's needed: For accountability, compliance, and debugging. If an attack slips through,
    the audit log is the primary tool to discover what happened and improve the guardrails.
    """
    def __init__(self):
        super().__init__(name="audit_log")
        self.logs = []
        self._start_time = None

    def _extract_text(self, content_obj) -> str:
        text = ""
        if hasattr(content_obj, "content"):
            content_obj = content_obj.content
        if hasattr(content_obj, 'parts') and content_obj.parts:
            for p in content_obj.parts:
                if hasattr(p, 'text') and p.text:
                    text += p.text
        elif isinstance(content_obj, str):
            text = content_obj
        return text

    async def on_user_message_callback(self, invocation_context=None, user_message=None, **kwargs):
        """Record input + start time. Never blocks the pipeline."""
        if invocation_context is None: invocation_context = kwargs.get('invocation_context')
        if user_message is None: user_message = kwargs.get('user_message')
        self._start_time = time.time()
        
        input_text = self._extract_text(user_message)
        if hasattr(user_message, 'parts') and not input_text:
           # ADK message parsing fallback
           try:
               input_text = user_message.parts[0].text
           except:
               pass

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "input_message": input_text,
            "blocked": False,
            "latency_ms": 0,
            "response": ""
        }
        self.logs.append(log_entry)
        return None  # Let the request pass

    async def after_model_callback(self, callback_context=None, llm_response=None, **kwargs):
        """Plugin model callback."""
        return llm_response

    def log_final_response(self, out_text: str):
        """Call this from main script after the stream finishes to log the full text."""
        if not self.logs: return
        latest_log = self.logs[-1]
        latest_log["response"] = out_text
        if "[BLOCKED]" in out_text or "[REDACTED]" in out_text or "unable" in out_text.lower():
             latest_log["blocked"] = True
        if self._start_time:
            latest_log["latency_ms"] = round((time.time() - self._start_time) * 1000, 2)

    def export_json(self, filepath="audit_log.json"):
        """Export all captured events to a JSON file."""
        with open(filepath, "w", encoding='utf-8') as f:
            json.dump(self.logs, f, indent=2, ensure_ascii=False)
