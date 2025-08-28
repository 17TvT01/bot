import json
import os
import time
import threading
import datetime
from typing import Dict, List, Optional
import random

class TaskManager:
    def __init__(self):
        self.tasks_file = "tasks.json"
        self.tasks = self._load_tasks()
        
    def _load_tasks(self) -> List[Dict]:
        """Load tasks from file."""
        if os.path.exists(self.tasks_file):
            try:
                with open(self.tasks_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def _save_tasks(self):
        """Save tasks to file."""
        with open(self.tasks_file, 'w', encoding='utf-8') as f:
            json.dump(self.tasks, f, ensure_ascii=False, indent=2)
    
    def add_task(self, task_description: str, priority: str = "medium") -> str:
        """Add a new task."""
        task = {
            "id": len(self.tasks) + 1,
            "description": task_description,
            "priority": priority,
            "completed": False,
            "created_at": datetime.datetime.now().isoformat(),
            "completed_at": None
        }
        self.tasks.append(task)
        self._save_tasks()
        return f"Đã thêm task: {task_description} (Ưu tiên: {priority})"
    
    def list_tasks(self, show_completed: bool = False) -> str:
        """List all tasks."""
        if not self.tasks:
            return "Không có task nào."
        
        filtered_tasks = [t for t in self.tasks if show_completed or not t['completed']]
        
        if not filtered_tasks:
            return "Không có task đang chờ."
        
        result = "📋 Danh sách task:\n"
        for task in filtered_tasks:
            status = "✅" if task['completed'] else "⏳"
            priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(task['priority'], "⚪")
            result += f"{status} {priority_emoji} {task['id']}. {task['description']}\n"
        
        return result
    
    def complete_task(self, task_id: int) -> str:
        """Mark a task as completed."""
        for task in self.tasks:
            if task['id'] == task_id:
                task['completed'] = True
                task['completed_at'] = datetime.datetime.now().isoformat()
                self._save_tasks()
                return f"✅ Đã hoàn thành task: {task['description']}"
        return "❌ Không tìm thấy task với ID này."
    
    def clear_completed(self) -> str:
        """Remove all completed tasks."""
        completed_count = sum(1 for t in self.tasks if t['completed'])
        self.tasks = [t for t in self.tasks if not t['completed']]
        self._save_tasks()
        return f"🧹 Đã xóa {completed_count} task đã hoàn thành."

class PomodoroTimer:
    def __init__(self):
        self.is_running = False
        self.remaining_time = 0
        self.work_duration = 25 * 60  # 25 minutes
        self.break_duration = 5 * 60   # 5 minutes
        self.current_cycle = 0
        self.max_cycles = 4
        self.timer_thread = None
        
    def start_work(self, minutes: int = 25) -> str:
        """Start a work session."""
        if self.is_running:
            return "⏰ Timer đang chạy. Hãy kết thúc hoặc tạm dừng trước."
        
        self.work_duration = minutes * 60
        self.remaining_time = self.work_duration
        self.is_running = True
        self.current_cycle += 1
        
        self.timer_thread = threading.Thread(target=self._run_timer, daemon=True)
        self.timer_thread.start()
        
        return f"🍅 Bắt đầu làm việc {minutes} phút! (Chu kỳ {self.current_cycle}/{self.max_cycles})"
    
    def start_break(self, minutes: int = 5) -> str:
        """Start a break session."""
        if self.is_running:
            return "⏰ Timer đang chạy."
        
        self.break_duration = minutes * 60
        self.remaining_time = self.break_duration
        self.is_running = True
        
        self.timer_thread = threading.Thread(target=self._run_timer, daemon=True)
        self.timer_thread.start()
        
        return f"☕ Bắt đầu nghỉ ngơi {minutes} phút!"
    
    def _run_timer(self):
        """Run the timer in background."""
        while self.remaining_time > 0 and self.is_running:
            time.sleep(1)
            self.remaining_time -= 1
        
        if self.is_running:
            self.is_running = False
            if self.remaining_time == 0:
                # Timer completed
                if self.remaining_time == self.work_duration:
                    # Work session completed
                    if self.current_cycle >= self.max_cycles:
                        self._notify("🎉 Hoàn thành tất cả chu kỳ! Nghỉ dài thôi!")
                    else:
                        self._notify("⏰ Hết giờ làm việc! Đến lúc nghỉ ngơi.")
                else:
                    # Break completed
                    self._notify("⏰ Hết giờ nghỉ! Quay lại làm việc thôi!")
    
    def _notify(self, message: str):
        """Send notification (could be enhanced with system notifications)."""
        print(f"NOTIFICATION: {message}")
    
    def stop(self) -> str:
        """Stop the current timer."""
        if not self.is_running:
            return "⏰ Không có timer nào đang chạy."
        
        self.is_running = False
        if self.timer_thread:
            self.timer_thread.join(timeout=1)
        
        minutes = self.remaining_time // 60
        seconds = self.remaining_time % 60
        return f"⏹️ Đã dừng timer. Còn lại: {minutes} phút {seconds} giây."
    
    def status(self) -> str:
        """Get current timer status."""
        if not self.is_running:
            return "⏰ Timer không hoạt động."
        
        minutes = self.remaining_time // 60
        seconds = self.remaining_time % 60
        
        if self.remaining_time == self.work_duration:
            session_type = "Làm việc"
        else:
            session_type = "Nghỉ ngơi"
        
        return f"⏰ {session_type}: {minutes:02d}:{seconds:02d} (Chu kỳ {self.current_cycle}/{self.max_cycles})"

class Entertainment:
    def __init__(self):
        self.jokes = [
            "Tại sao developer không thích thiên nhiên? Vì có quá nhiều bugs!",
            "Có 10 loại người trên thế giới: những người hiểu nhị phân và những người không.",
            "Tại sao programmer luôn nhầm lẫn giữa Halloween và Christmas? Vì Oct 31 == Dec 25!",
            "Một SQL query đi vào quán bar, tiếp cận hai bàn và hỏi: 'Tôi có thể JOIN các bạn không?'",
            "Tại sao Python programmer không cần bạn gái? Vì họ đã có import antigravity!"
        ]
        
        self.quotes = [
            "Đừng sợ thất bại. Hãy sợ việc không dám thử.",
            "Thành công không phải là đích đến, mà là hành trình.",
            "Mỗi ngày là một cơ hội mới để trở nên tốt hơn.",
            "Đam mê + Kiên trì = Thành công",
            "Học, học nữa, học mãi - cho đến khi bug được fix!"
        ]
    
    def tell_joke(self) -> str:
        """Tell a random joke."""
        return f"😂 {random.choice(self.jokes)}"
    
    def inspire(self) -> str:
        """Give an inspirational quote."""
        return f"💫 {random.choice(self.quotes)}"
    
    def play_game(self, game_type: str = "") -> str:
        """Play a simple game."""
        games = {
            "coin": self._flip_coin,
            "dice": self._roll_dice,
            "number": self._random_number
        }
        
        if game_type in games:
            return games[game_type]()
        else:
            return "🎮 Trò chơi có sẵn: tung đồng xu, xúc xắc, số ngẫu nhiên"
    
    def _flip_coin(self) -> str:
        """Flip a coin."""
        result = "Mặt ngửa" if random.random() > 0.5 else "Mặt sấp"
        return f"🪙 Tung đồng xu: {result}"
    
    def _roll_dice(self) -> str:
        """Roll a dice."""
        result = random.randint(1, 6)
        return f"🎲 Xúc xắc: {result}"
    
    def _random_number(self) -> str:
        """Generate a random number."""
        result = random.randint(1, 100)
        return f"🔢 Số ngẫu nhiên: {result}"

# Global instances
task_manager = TaskManager()
pomodoro_timer = PomodoroTimer()
entertainment = Entertainment()

def work_assistant(command: str = None) -> str:
    """Main work assistant feature."""
    if not command:
        return get_help()
    
    tokens = command.lower().split()
    
    # Task management
    if any(word in tokens for word in ["task", "nhiệm vụ", "công việc", "thêm task"]):
        if "thêm" in tokens or "add" in tokens:
            task_desc = command.split("thêm")[-1].split("add")[-1].strip()
            if task_desc:
                priority = "high" if "quan trọng" in tokens else "medium"
                return task_manager.add_task(task_desc, priority)
        
        elif "xem" in tokens or "list" in tokens or "hiển thị" in tokens:
            show_all = "tất cả" in tokens or "all" in tokens
            return task_manager.list_tasks(show_all)
        
        elif "hoàn thành" in tokens or "complete" in tokens:
            try:
                task_id = int(''.join(filter(str.isdigit, command)))
                return task_manager.complete_task(task_id)
            except:
                return "Vui lòng cung cấp ID task hợp lệ."
        
        elif "xóa" in tokens or "clear" in tokens:
            return task_manager.clear_completed()
    
    # Pomodoro timer
    elif any(word in tokens for word in ["pomodoro", "timer", "hẹn giờ", "làm việc"]):
        if "bắt đầu" in tokens or "start" in tokens:
            if "nghỉ" in tokens or "break" in tokens:
                minutes = 5
                if "phút" in tokens:
                    try:
                        minutes = int(''.join(filter(str.isdigit, command.split("phút")[0])))
                    except:
                        pass
                return pomodoro_timer.start_break(minutes)
            else:
                minutes = 25
                if "phút" in tokens:
                    try:
                        minutes = int(''.join(filter(str.isdigit, command.split("phút")[0])))
                    except:
                        pass
                return pomodoro_timer.start_work(minutes)
        
        elif "dừng" in tokens or "stop" in tokens:
            return pomodoro_timer.stop()
        
        elif "trạng thái" in tokens or "status" in tokens:
            return pomodoro_timer.status()
    
    # Entertainment
    elif any(word in tokens for word in ["giải trí", "đùa", "joke", "câu nói", "trò chơi"]):
        if "đùa" in tokens or "joke" in tokens:
            return entertainment.tell_joke()
        elif "câu nói" in tokens or "quote" in tokens:
            return entertainment.inspire()
        elif "trò chơi" in tokens or "game" in tokens:
            if "xu" in tokens or "coin" in tokens:
                return entertainment.play_game("coin")
            elif "xúc xắc" in tokens or "dice" in tokens:
                return entertainment.play_game("dice")
            elif "số" in tokens or "number" in tokens:
                return entertainment.play_game("number")
            else:
                return entertainment.play_game()
    
    return get_help()

def get_help() -> str:
    """Get help information."""
    return """🎯 Hỗ trợ công việc - Hướng dẫn sử dụng:

📋 Quản lý Task:
• "thêm task [mô tả]" - Thêm task mới
• "xem task" - Xem task đang chờ
• "xem tất cả task" - Xem cả task đã hoàn thành
• "hoàn thành task [id]" - Đánh dấu task hoàn thành
• "xóa task đã hoàn thành" - Xóa task đã xong

🍅 Pomodoro Timer:
• "bắt đầu làm việc [phút]" - Bắt đầu phiên làm việc
• "bắt đầu nghỉ [phút]" - Bắt đầu nghỉ ngơi
• "dừng timer" - Dừng timer hiện tại
• "trạng thái timer" - Xem trạng thái timer

🎮 Giải trí:
• "kể chuyện đùa" - Kể chuyện cười
• "câu nói truyền cảm hứng" - Câu nói hay
• "chơi game" - Trò chơi đơn giản

Hãy thử một trong các lệnh trên!"""

# Keywords and patterns for feature detection
keywords = [
    "task", "nhiệm vụ", "công việc", "pomodoro", "timer", 
    "hẹn giờ", "giải trí", "đùa", "trò chơi", "game"
]

patterns = [
    "thêm task",
    "xem task",
    "bắt đầu làm việc",
    "bắt đầu nghỉ ngơi",
    "kể chuyện đùa",
    "chơi game"
]
