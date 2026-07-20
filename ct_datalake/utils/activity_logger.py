"""
CT Group — Frappe Activity Logger Utility
==========================================
Dùng chung cho app CT DataLake.

Cách dùng:
    from ct_datalake.utils.activity_logger import ActivityLogger

    logger = ActivityLogger(prefix="DL", module="CT DataLake")

    # 1. Tạo session khi user vào app
    session_name = logger.create_session(session_id, dept="PAI", role="M")

    # 2. Ghi action log khi user thực hiện một tác vụ
    action_name = logger.start_action(session_name, action_type="semantic_search",
                                      input_summary="query=AI engineer, mode=in",
                                      input_detail={"query": "AI engineer"})

    # 3. Ghi AI call log mỗi lần gọi LLM
    logger.log_ai_call(session_name, action_name,
                       call_type="jd_match", ai_model="gpt-4o",
                       prompt_tokens=1200, completion_tokens=800,
                       duration_seconds=4.2, status="success")

    # 4. Hoàn thành action
    logger.finish_action(action_name, status="success",
                         output_summary="Tìm thấy 5 ứng viên...",
                         duration_seconds=4.5)
"""

import frappe
from frappe.utils import now_datetime
import time


class ActivityLogger:
    def __init__(self, prefix: str, module: str):
        """
        prefix: Tiền tố DocType, VD: "DL"
        module: Tên module Frappe, VD: "CT DataLake"
        """
        self.prefix = prefix
        self.module = module
        self.session_dt  = f"{prefix} Session"
        self.action_dt   = f"{prefix} Action Log"
        self.ai_call_dt  = f"{prefix} AI Call Log"

    # ─────────────────────────────────────────────
    # SESSION
    # ─────────────────────────────────────────────

    def create_session(self, session_id: str, dept: str = "", role: str = "") -> str:
        """Tạo session mới. Trả về tên document."""
        try:
            ip = frappe.local.request_ip if hasattr(frappe.local, "request_ip") else ""
            ua = ""
            if hasattr(frappe.local, "request") and frappe.local.request:
                ua = frappe.local.request.environ.get("HTTP_USER_AGENT", "")[:500]

            doc = frappe.get_doc({
                "doctype": self.session_dt,
                "session_id": session_id,
                "user": frappe.session.user,
                "ip_address": ip,
                "user_agent": ua,
                "department": dept,
                "role_param": role,
                "started_at": now_datetime(),
                "last_active_at": now_datetime(),
                "status": "active",
            })
            doc.insert(ignore_permissions=True)
            frappe.db.commit()
            return doc.name
        except Exception as e:
            try: frappe.db.rollback()
            except: pass
            try: frappe.log_error(f"ActivityLogger.create_session failed: {e}")
            except: pass
            return ""

    def update_session_active(self, session_name: str):
        """Cập nhật last_active_at."""
        try:
            frappe.db.set_value(self.session_dt, session_name,
                                "last_active_at", now_datetime(),
                                update_modified=False)
        except Exception:
            pass

    def finish_session(self, session_name: str):
        """Đánh dấu session hoàn thành."""
        try:
            frappe.db.set_value(self.session_dt, session_name, {
                "status": "completed",
                "last_active_at": now_datetime(),
            }, update_modified=False)
        except Exception:
            pass

    def _increment_session_counters(self, session_name: str,
                                    actions: int = 0, ai_calls: int = 0,
                                    prompt_tokens: int = 0, completion_tokens: int = 0,
                                    ai_model: str = ""):
        """Tăng counter trong session. Gọi sau mỗi action/ai_call."""
        if not session_name:
            return
        try:
            # ignore_permissions=True bắt buộc: user thường không có read permission
            sess = frappe.get_doc(self.session_dt, session_name, ignore_permissions=True)
            sess.total_actions           = (sess.total_actions or 0) + actions
            sess.total_ai_calls          = (sess.total_ai_calls or 0) + ai_calls
            sess.total_prompt_tokens     = (sess.total_prompt_tokens or 0) + prompt_tokens
            sess.total_completion_tokens = (sess.total_completion_tokens or 0) + completion_tokens
            sess.total_tokens_used      = (sess.total_tokens_used or 0) + prompt_tokens + completion_tokens
            
            if ai_model and (prompt_tokens > 0 or completion_tokens > 0):
                import json
                try:
                    breakdown = json.loads(sess.token_breakdown) if sess.token_breakdown else {}
                except:
                    breakdown = {}
                
                current = breakdown.get(ai_model, {"input": 0, "output": 0})
                if isinstance(current, int):
                    current = {"input": current, "output": 0}
                elif not isinstance(current, dict):
                    current = {"input": 0, "output": 0}
                    
                current["input"] += prompt_tokens
                current["output"] += completion_tokens
                breakdown[ai_model] = current
                
                sess.token_breakdown = json.dumps(breakdown, ensure_ascii=False)
                
            sess.last_active_at          = now_datetime()
            sess.save(ignore_permissions=True)
            frappe.db.commit()
        except Exception as e:
            try: frappe.db.rollback()
            except: pass
            try: frappe.log_error(f"ActivityLogger._increment_session_counters: {e}")
            except: pass


    # ─────────────────────────────────────────────
    # ACTION LOG
    # ─────────────────────────────────────────────

    def start_action(self, session_name: str, action_type: str,
                     input_summary: str = "", input_detail: dict = None) -> str:
        """Tạo action log với status=running. Trả về tên document."""
        try:
            import json
            doc = frappe.get_doc({
                "doctype": self.action_dt,
                "session": session_name,
                "user": frappe.session.user,
                "action_type": action_type,
                "timestamp": now_datetime(),
                "input_summary": input_summary[:500] if input_summary else "",
                "input_detail": json.dumps(input_detail or {}, ensure_ascii=False)[:2000],
                "status": "running",
            })
            doc.insert(ignore_permissions=True)
            frappe.db.commit()
            self._increment_session_counters(session_name, actions=1)
            return doc.name
        except Exception as e:
            try: frappe.db.rollback()
            except: pass
            try: frappe.log_error(f"ActivityLogger.start_action failed: {e}")
            except: pass
            return ""

    def finish_action(self, action_name: str, status: str = "success",
                      output_summary: str = "", error_message: str = "",
                      ai_model: str = "", from_cache: bool = False,
                      prompt_tokens: int = 0, completion_tokens: int = 0,
                      duration_seconds: float = 0.0):
        """Cập nhật action log sau khi hoàn thành."""
        if not action_name:
            return
        try:
            frappe.db.set_value(self.action_dt, action_name, {
                "status": status,
                "output_summary": output_summary[:500] if output_summary else "",
                "error_message": error_message[:500] if error_message else "",
                "ai_model": ai_model,
                "from_cache": 1 if from_cache else 0,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
                "duration_seconds": round(duration_seconds, 3),
            }, update_modified=False)
            frappe.db.commit()
        except Exception as e:
            try: frappe.db.rollback()
            except: pass
            try: frappe.log_error(f"ActivityLogger.finish_action failed: {e}")
            except: pass

    # ─────────────────────────────────────────────
    # AI CALL LOG
    # ─────────────────────────────────────────────

    def log_ai_call(self, session_name: str, action_name: str,
                    call_type: str, ai_model: str,
                    prompt_tokens: int = 0, completion_tokens: int = 0,
                    duration_seconds: float = 0.0,
                    status: str = "success",
                    attempt_number: int = 1,
                    error_code: str = "", error_message: str = "") -> str:
        """Ghi một lần gọi AI. Trả về tên document."""
        try:
            doc = frappe.get_doc({
                "doctype": self.ai_call_dt,
                "session": session_name,
                "action_log": action_name,
                "user": frappe.session.user,
                "timestamp": now_datetime(),
                "call_type": call_type,
                "ai_model": ai_model,
                "attempt_number": attempt_number,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
                "duration_seconds": round(duration_seconds, 3),
                "status": status,
                "error_code": error_code,
                "error_message": error_message[:500] if error_message else "",
            })
            doc.insert(ignore_permissions=True)
            frappe.db.commit()
            self._increment_session_counters(
                session_name, ai_calls=1,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                ai_model=ai_model
            )
            return doc.name
        except Exception as e:
            try: frappe.db.rollback()
            except: pass
            try: frappe.log_error(f"ActivityLogger.log_ai_call failed: {e}")
            except: pass
            return ""


# ─────────────────────────────────────────────────────────
# HELPER: Timer context manager
# ─────────────────────────────────────────────────────────

class Timer:
    """Dùng với `with Timer() as t:` rồi lấy `t.elapsed`."""
    def __enter__(self):
        self._start = time.time()
        return self

    def __exit__(self, *args):
        self.elapsed = round(time.time() - self._start, 3)
