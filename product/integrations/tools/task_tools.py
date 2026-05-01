"""
Task Tools - Task and action management.

Handles:
- hcr_get_current_task: Get current task context
- hcr_get_next_action: Get recommended next action
"""

from typing import Any, Dict
from .base_tool import BaseMCPTool


class GetCurrentTaskTool(BaseMCPTool):
    """Get current task from engine context inference"""
    
    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get current task context.
        
        Args:
            use_llm: Whether to use LLM for smart summary (slower)
            session_id: Session for snapshot recording
            
        Returns:
            Formatted task summary with progress
        """
        use_llm = args.get("use_llm", False)
        session_id = args.get("session_id")
        
        engine = self._get_engine()
        if not engine:
            return {"content": "HCR Engine not initialized. Please run 'hcr init' first.", "task": None}
        
        # Infer current context with timeout
        try:
            context = await self._run_blocking(lambda: engine.infer_context(use_llm=use_llm), timeout=3.0)
        except Exception as e:
            self.logger.warning(f"Task inference failed: {e}")
            from src.engine_api import EngineContext
            context = EngineContext(
                current_task="Unknown",
                progress_percent=0,
                next_action="Initialize HCR",
                confidence=0.0,
                gap_minutes=0,
                facts=[]
            )
        
        # Generate formatted summary (via responder if available)
        summary = context.current_task
        if self.responder and hasattr(self.responder, '_generate_smart_resume'):
            try:
                summary = await self.responder._generate_smart_resume(
                    context, use_llm=use_llm, mode="resume", session_id=session_id
                )
            except Exception as e:
                self.logger.warning(f"Smart resume generation failed: {e}")
                summary = f"**Current Task:** {context.current_task}\n**Progress:** {context.progress_percent}%"
        
        # Record snapshot via responder
        if self.responder and hasattr(self.responder, '_record_session_snapshot'):
            self.responder._record_session_snapshot(session_id, summary, {
                "task": context.current_task,
                "progress_percent": context.progress_percent,
                "mode": "resume"
            })
        
        return {
            "content": summary,
            "task": context.current_task,
            "progress_percent": context.progress_percent
        }


class GetNextActionTool(BaseMCPTool):
    """Get next action suggestion from engine"""
    
    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get recommended next action.
        
        Args:
            use_llm: Whether to use LLM for smart suggestion (slower)
            session_id: Session for snapshot recording
            
        Returns:
            Formatted action recommendation with confidence
        """
        use_llm = args.get("use_llm", False)
        session_id = args.get("session_id")
        
        engine = self._get_engine()
        if not engine:
            return {"content": "HCR Engine not initialized. Please run 'hcr init' first.", "next_action": None}
        
        # Infer current context with timeout
        try:
            context = await self._run_blocking(lambda: engine.infer_context(use_llm=use_llm), timeout=3.0)
        except Exception as e:
            self.logger.warning(f"Next action inference failed: {e}")
            from src.engine_api import EngineContext
            context = EngineContext(
                current_task="Unknown",
                progress_percent=0,
                next_action="Initialize HCR",
                confidence=0.0,
                gap_minutes=0,
                facts=[]
            )
        
        # Generate formatted summary (via responder if available)
        summary = context.next_action
        if self.responder and hasattr(self.responder, '_generate_smart_resume'):
            try:
                summary = await self.responder._generate_smart_resume(
                    context, use_llm=use_llm, mode="action", session_id=session_id
                )
            except Exception as e:
                self.logger.warning(f"Smart action generation failed: {e}")
                summary = f"**Next Action:** {context.next_action}\n**Confidence:** {context.confidence:.0%}"
        
        # Record snapshot via responder
        if self.responder and hasattr(self.responder, '_record_session_snapshot'):
            self.responder._record_session_snapshot(session_id, summary, {
                "next_action": context.next_action,
                "confidence": context.confidence,
                "mode": "action"
            })
        
        return {
            "content": summary,
            "next_action": context.next_action,
            "confidence": context.confidence
        }
