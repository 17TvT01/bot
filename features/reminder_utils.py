import datetime
from typing import Optional

try:
    from .reminder import get_reminder_manager  # type: ignore
except Exception:
    get_reminder_manager = None  # type: ignore

def snooze_by_id(reminder_id: str, minutes: int = 10) -> str:
    """Best-effort snooze using ReminderManager internals without modifying its code.

    If the manager exposes a 'snooze_reminder' method, use it. Otherwise, update the
    reminder time directly and reschedule by calling private helpers when available.
    """
    if not get_reminder_manager:
        return "Hệ thống nhắc nhở chưa sẵn sàng."
    rm = get_reminder_manager()
    # Use native method if present
    if hasattr(rm, 'snooze_reminder'):
        try:
            return rm.snooze_reminder(reminder_id, minutes)  # type: ignore
        except Exception as e:
            return f"Không thể hoãn: {e}"
    # Fallback: adjust time in-place
    try:
        for r in getattr(rm, 'reminders', []) or []:
            if str(r.get('id')) == str(reminder_id):
                t = r.get('time')
                if isinstance(t, datetime.datetime):
                    new_t = t + datetime.timedelta(minutes=minutes)
                else:
                    try:
                        tt = datetime.datetime.fromisoformat(str(t))
                        new_t = tt + datetime.timedelta(minutes=minutes)
                    except Exception:
                        new_t = datetime.datetime.now() + datetime.timedelta(minutes=minutes)
                r['time'] = new_t
                try:
                    rm.save_reminders()
                except Exception:
                    pass
                try:
                    # Reschedule if helper exists
                    if hasattr(rm, '_schedule_reminder'):
                        rm._schedule_reminder(r)  # type: ignore
                except Exception:
                    pass
                return f"Đã hoãn nhắc nhở {reminder_id} thêm {minutes} phút."
        return "Không tìm thấy nhắc nhở để hoãn."
    except Exception as e:
        return f"Không thể hoãn: {e}"

