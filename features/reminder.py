import datetime
import json
import os
import re
import threading
import time
from typing import Dict, List, Optional, Tuple

# Đường dẫn đến tệp lưu trữ dữ liệu nhắc nhở
REMINDER_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "reminder_data.json")

# Từ khóa và mẫu cho việc nhận diện tính năng
keywords = ["nhắc nhở", "lịch", "sự kiện", "hẹn", "lịch trình", "reminder", "calendar", "event", "ghi chú"]

patterns = [
    "nhắc tôi",
    "thêm nhắc nhở",
    "tạo nhắc nhở",
    "lịch hôm nay",
    "lịch ngày mai",
    "lịch tuần này",
    "lịch tháng này",
    "xem lịch",
    "xem nhắc nhở",
    "xóa nhắc nhở",
    "hủy nhắc nhở",
    "xóa ghi chú",
    "hủy ghi chú",
    "xóa sự kiện",
    "hủy sự kiện",
    "có sự kiện gì",
    "có lịch gì",
    "có ghi chú gì"
]

class ReminderManager:
    """Quản lý các nhắc nhở và sự kiện trong lịch"""
    
    def __init__(self):
        self.reminders = []
        self.active_reminders = {}
        self.reminder_lock = threading.Lock()
        self.load_reminders()
        self.start_reminder_thread()
    
    def load_reminders(self) -> None:
        """Tải dữ liệu nhắc nhở từ tệp"""
        try:
            if os.path.exists(REMINDER_FILE):
                with open(REMINDER_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.reminders = data.get('reminders', [])
                    
                    # Chuyển đổi chuỗi thời gian thành đối tượng datetime
                    for reminder in self.reminders:
                        # Chuyển đổi tất cả các trường datetime
                        for key, value in reminder.items():
                            if isinstance(value, str) and key in ['time', 'created']:
                                try:
                                    reminder[key] = datetime.datetime.fromisoformat(value)
                                except ValueError:
                                    # Nếu không thể chuyển đổi, giữ nguyên giá trị chuỗi
                                    pass
        except Exception as e:
            print(f"Lỗi khi tải dữ liệu nhắc nhở: {e}")
            self.reminders = []
    
    def save_reminders(self) -> None:
        """Lưu dữ liệu nhắc nhở vào tệp"""
        try:
            # Chuyển đổi đối tượng datetime thành chuỗi trước khi lưu
            serializable_reminders = []
            for reminder in self.reminders:
                reminder_copy = reminder.copy()
                # Chuyển đổi tất cả các trường datetime thành chuỗi
                for key, value in reminder_copy.items():
                    if isinstance(value, datetime.datetime):
                        reminder_copy[key] = value.isoformat()
                serializable_reminders.append(reminder_copy)
                
            with open(REMINDER_FILE, 'w', encoding='utf-8') as f:
                json.dump({'reminders': serializable_reminders}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Lỗi khi lưu dữ liệu nhắc nhở: {e}")
    
    def add_reminder(self, title: str, time_str: str, description: str = "") -> str:
        """Thêm một nhắc nhở mới"""
        try:
            # Phân tích chuỗi thời gian
            reminder_time = self._parse_time(time_str)
            if not reminder_time:
                return "Không thể nhận dạng thời gian. Vui lòng sử dụng định dạng như 'ngày mai 8h', '15/05/2023 14:30'."
            
            # Tạo ID duy nhất cho nhắc nhở
            reminder_id = str(int(time.time()))
            
            # Tạo nhắc nhở mới
            reminder = {
                'id': reminder_id,
                'title': title,
                'description': description,
                'time': reminder_time,
                'created': datetime.datetime.now()
            }
            
            # Thêm vào danh sách và lưu
            with self.reminder_lock:
                self.reminders.append(reminder)
                self.save_reminders()
                
                # Nếu nhắc nhở trong tương lai, thêm vào danh sách theo dõi
                if reminder_time > datetime.datetime.now():
                    self._schedule_reminder(reminder)
            
            # Định dạng thời gian để hiển thị
            time_display = reminder_time.strftime("%H:%M ngày %d/%m/%Y")
            return f"Đã thêm nhắc nhở: {title} vào lúc {time_display}"
            
        except Exception as e:
            return f"Lỗi khi thêm nhắc nhở: {str(e)}"
    
    def _parse_time(self, time_str: str) -> Optional[datetime.datetime]:
        """Phân tích chuỗi thời gian thành đối tượng datetime"""
        now = datetime.datetime.now()
        time_str = time_str.lower()
        
        try:
            # Xử lý các từ khóa thời gian tương đối
            if "hôm nay" in time_str or "today" in time_str:
                date = now.date()
            elif "ngày mai" in time_str or "tomorrow" in time_str:
                date = (now + datetime.timedelta(days=1)).date()
            elif "tuần sau" in time_str or "next week" in time_str:
                date = (now + datetime.timedelta(days=7)).date()
            else:
                # Thử phân tích ngày tháng từ chuỗi
                # Hỗ trợ các định dạng: DD/MM/YYYY, DD-MM-YYYY
                date_match = None
                for pattern in [r'(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?', r'(\d{1,2}) tháng (\d{1,2})(?: năm (\d{2,4}))?']:
                    match = re.search(pattern, time_str)
                    if match:
                        date_match = match
                        break
                
                if date_match:
                    day = int(date_match.group(1))
                    month = int(date_match.group(2))
                    year = int(date_match.group(3)) if date_match.group(3) else now.year
                    
                    # Xử lý năm 2 chữ số
                    if year < 100:
                        year += 2000
                        
                    date = datetime.date(year, month, day)
                else:
                    date = now.date()
            
            # Xử lý giờ
            hour, minute = 8, 0  # Mặc định 8:00 sáng
            
            # Tìm giờ trong chuỗi
            hour_match = re.search(r'(\d{1,2})[:](\d{1,2})', time_str)
            if hour_match:
                hour = int(hour_match.group(1))
                minute = int(hour_match.group(2))
            else:
                # Tìm giờ dạng "8h", "14 giờ", "15h30"
                hour_match = re.search(r'(\d{1,2})\s*(?:h|giờ)\s*(\d{1,2})?', time_str)
                if hour_match:
                    hour = int(hour_match.group(1))
                    minute = int(hour_match.group(2)) if hour_match.group(2) else 0
            
            # Tạo đối tượng datetime
            reminder_time = datetime.datetime.combine(date, datetime.time(hour, minute))
            
            # Nếu thời gian đã qua trong ngày hôm nay, đặt vào ngày mai
            if reminder_time < now and "hôm nay" in time_str:
                reminder_time += datetime.timedelta(days=1)
                
            return reminder_time
            
        except Exception as e:
            print(f"Lỗi khi phân tích thời gian: {e}")
            return None
    
    def list_reminders(self, filter_str: str = None) -> str:
        """Liệt kê các nhắc nhở"""
        with self.reminder_lock:
            if not self.reminders:
                return "Bạn chưa có nhắc nhở nào."
            
            # Lọc nhắc nhở nếu có yêu cầu
            filtered_reminders = self.reminders
            if filter_str:
                filter_str = filter_str.lower()
                if "hôm nay" in filter_str or "today" in filter_str:
                    today = datetime.datetime.now().date()
                    filtered_reminders = [r for r in self.reminders 
                                         if isinstance(r.get('time'), datetime.datetime) 
                                         and r['time'].date() == today]
                elif "ngày mai" in filter_str or "tomorrow" in filter_str:
                    tomorrow = (datetime.datetime.now() + datetime.timedelta(days=1)).date()
                    filtered_reminders = [r for r in self.reminders 
                                         if isinstance(r.get('time'), datetime.datetime) 
                                         and r['time'].date() == tomorrow]
                elif "tuần này" in filter_str or "this week" in filter_str:
                    today = datetime.datetime.now().date()
                    end_of_week = today + datetime.timedelta(days=(6 - today.weekday()))
                    filtered_reminders = [r for r in self.reminders 
                                         if isinstance(r.get('time'), datetime.datetime) 
                                         and today <= r['time'].date() <= end_of_week]
                else:
                    # Lọc theo từ khóa trong tiêu đề hoặc mô tả
                    filtered_reminders = [r for r in self.reminders 
                                         if filter_str in r['title'].lower() 
                                         or filter_str in r.get('description', '').lower()]
            
            # Sắp xếp theo thời gian
            filtered_reminders.sort(key=lambda x: x['time'] if isinstance(x.get('time'), datetime.datetime) else datetime.datetime.max)
            
            # Tạo danh sách hiển thị
            if not filtered_reminders:
                return "Không tìm thấy nhắc nhở nào phù hợp với yêu cầu."
                
            result = "📅 Danh sách nhắc nhở:\n\n"
            for i, reminder in enumerate(filtered_reminders, 1):
                time_str = reminder['time'].strftime("%H:%M ngày %d/%m/%Y") if isinstance(reminder.get('time'), datetime.datetime) else "Không xác định"
                desc = f" - {reminder['description']}" if reminder.get('description') else ""
                result += f"{i}. {reminder['title']} ({time_str}){desc} [ID: {reminder['id']}]\n"
                
            return result
    
    def delete_reminder(self, reminder_id: str) -> str:
        """Xóa một nhắc nhở theo ID"""
        with self.reminder_lock:
            # Tìm nhắc nhở theo ID
            for i, reminder in enumerate(self.reminders):
                if reminder['id'] == reminder_id:
                    # Xóa khỏi danh sách và lưu
                    removed = self.reminders.pop(i)
                    self.save_reminders()
                    
                    # Xóa khỏi danh sách theo dõi nếu có
                    if reminder_id in self.active_reminders:
                        self.active_reminders.pop(reminder_id)
                        
                    return f"Đã xóa nhắc nhở: {removed['title']}"
            
            return "Không tìm thấy nhắc nhở với ID đã cung cấp."
    
    def _schedule_reminder(self, reminder: Dict) -> None:
        """Lên lịch cho một nhắc nhở"""
        reminder_id = reminder['id']
        reminder_time = reminder['time']
        
        # Tính thời gian chờ (giây)
        now = datetime.datetime.now()
        wait_seconds = (reminder_time - now).total_seconds()
        
        if wait_seconds <= 0:
            return
        
        # Tạo timer để kích hoạt nhắc nhở
        timer = threading.Timer(wait_seconds, self._trigger_reminder, args=[reminder_id])
        timer.daemon = True
        timer.start()
        
        # Lưu timer để có thể hủy nếu cần
        self.active_reminders[reminder_id] = timer
    
    def _trigger_reminder(self, reminder_id: str) -> None:
        """Kích hoạt một nhắc nhở"""
        with self.reminder_lock:
            # Tìm nhắc nhở theo ID
            reminder = None
            for r in self.reminders:
                if r['id'] == reminder_id:
                    reminder = r
                    break
            
            if not reminder:
                return
            
            # Xóa khỏi danh sách theo dõi
            if reminder_id in self.active_reminders:
                self.active_reminders.pop(reminder_id)
            
            # Gửi thông báo
            self._send_notification(reminder)
    
    def _send_notification(self, reminder: Dict) -> None:
        """Gửi thông báo nhắc nhở"""
        # Đây là nơi để tích hợp với hệ thống thông báo
        # Trong phiên bản đơn giản, chỉ in ra console
        print(f"\n[NHẮC NHỞ] {reminder['title']}")
        if reminder.get('description'):
            print(f"Chi tiết: {reminder['description']}")
        
        # Thêm code để hiển thị thông báo trên GUI ở đây
        # Sẽ được tích hợp sau khi cập nhật GUI
    
    def start_reminder_thread(self) -> None:
        """Khởi động thread theo dõi các nhắc nhở"""
        def _monitor_reminders():
            while True:
                try:
                    # Lên lịch lại các nhắc nhở chưa kích hoạt
                    with self.reminder_lock:
                        now = datetime.datetime.now()
                        for reminder in self.reminders:
                            reminder_id = reminder['id']
                            reminder_time = reminder.get('time')
                            
                            # Bỏ qua nếu không phải datetime hoặc đã qua
                            if not isinstance(reminder_time, datetime.datetime) or reminder_time < now:
                                continue
                                
                            # Nếu chưa được lên lịch, thêm vào
                            if reminder_id not in self.active_reminders:
                                self._schedule_reminder(reminder)
                                
                except Exception as e:
                    print(f"Lỗi trong thread nhắc nhở: {e}")
                    
                # Kiểm tra mỗi 60 giây
                time.sleep(60)
        
        # Khởi động thread
        monitor_thread = threading.Thread(target=_monitor_reminders, daemon=True)
        monitor_thread.start()

# Singleton instance
_reminder_manager = None

def get_reminder_manager() -> ReminderManager:
    """Lấy instance của ReminderManager (singleton)"""
    global _reminder_manager
    if _reminder_manager is None:
        _reminder_manager = ReminderManager()
    return _reminder_manager

def reminder(command: str = None) -> str:
    """Hàm chính xử lý các lệnh liên quan đến nhắc nhở"""
    if not command:
        return "Tính năng nhắc nhở giúp bạn quản lý lịch và sự kiện. Sử dụng 'nhắc tôi <nội dung> vào <thời gian>' để tạo nhắc nhở mới."
    
    manager = get_reminder_manager()
    command = command.lower()
    
    # Xử lý lệnh xóa nhắc nhở - Kiểm tra trước để tránh xung đột với các từ khóa khác
    if any(phrase in command for phrase in ["xóa nhắc", "xóa nhắc nhở", "hủy nhắc", "hủy nhắc nhở", "xóa lịch", "xóa ghi chú", "xóa sự kiện", "hủy ghi chú", "hủy sự kiện", "hủy lịch"]):
        # Tìm ID nhắc nhở
        import re
        id_match = re.search(r'id[:\s]*(\d+)', command, re.IGNORECASE)
        
        # Tìm theo thời gian trong lệnh
        time_match = None
        time_patterns = [
            r'(\d{1,2})[\s]*(?:h|giờ)(?:[\s]*(\d{1,2}))?',  # 8h, 8 giờ, 8h30, 8 giờ 30
            r'(\d{1,2}):(\d{1,2})'  # 8:30
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, command)
            if match:
                time_match = match
                break
        
        # Kiểm tra từ khóa thời gian
        time_filter = None
        if "ngày mai" in command:
            time_filter = "ngày mai"
        elif "hôm nay" in command:
            time_filter = "hôm nay"
        
        # Nếu có thông tin về thời gian, tìm nhắc nhở theo thời gian
        if time_match or time_filter:
            hour = None
            minute = 0
            
            if time_match:
                if ':' in time_match.group(0):
                    hour = int(time_match.group(1))
                    minute = int(time_match.group(2))
                else:
                    hour = int(time_match.group(1))
                    minute = int(time_match.group(2)) if time_match.group(2) else 0
            
            with manager.reminder_lock:
                now = datetime.datetime.now()
                tomorrow = now + datetime.timedelta(days=1)
                
                for reminder in manager.reminders:
                    time_str = reminder.get('time')
                    if isinstance(time_str, datetime.datetime):
                        reminder_time = time_str
                    elif isinstance(time_str, str):
                        try:
                            reminder_time = datetime.datetime.fromisoformat(time_str)
                        except ValueError:
                            continue
                    else:
                        continue
                    
                    # Kiểm tra ngày
                    matches_day = True
                    if time_filter == "ngày mai" and reminder_time.date() != tomorrow.date():
                        matches_day = False
                    elif time_filter == "hôm nay" and reminder_time.date() != now.date():
                        matches_day = False
                    
                    # Kiểm tra giờ nếu có
                    matches_hour = True
                    if hour is not None and reminder_time.hour != hour:
                        matches_hour = False
                    
                    # Nếu khớp cả ngày và giờ
                    if matches_day and matches_hour:
                        return manager.delete_reminder(reminder['id'])
                
                return "Không tìm thấy nhắc nhở nào phù hợp với thời gian đã chỉ định."
        
        # Tìm theo từ khóa trong tiêu đề
        if not id_match:
            # Tìm từ khóa sau các từ như "xóa", "hủy"
            keywords = ["xóa", "hủy"]
            title_keywords = None
            
            for keyword in keywords:
                if keyword in command:
                    parts = command.split(keyword, 1)
                    if len(parts) > 1:
                        title_keywords = parts[1].strip()
                        break
            
            if title_keywords:
                # Loại bỏ các từ không cần thiết
                for word in ["nhắc nhở", "ghi chú", "lịch", "sự kiện", "giúp", "tôi", "cho", "của"]:
                    title_keywords = title_keywords.replace(word, "").strip()
                
                # Tìm nhắc nhở có tiêu đề chứa từ khóa
                if title_keywords:
                    with manager.reminder_lock:
                        for reminder in manager.reminders:
                            if title_keywords.lower() in reminder['title'].lower():
                                return manager.delete_reminder(reminder['id'])
                    
                    return f"Không tìm thấy nhắc nhở nào có nội dung '{title_keywords}'."
        
        if id_match:
            reminder_id = id_match.group(1)
            return manager.delete_reminder(reminder_id)
        else:
            # Hiển thị danh sách nhắc nhở để người dùng chọn
            reminders_list = manager.list_reminders()
            return f"Vui lòng chỉ định nhắc nhở cần xóa bằng ID hoặc nội dung cụ thể.\n\n{reminders_list}\n\nVí dụ: 'xóa nhắc nhở id:1234' hoặc 'xóa nhắc nhở cuộc họp'."
    
    # Xử lý lệnh thêm nhắc nhở - chỉ xử lý khi không phải là lệnh xóa
    elif any(phrase in command for phrase in ["nhắc tôi", "thêm nhắc nhở", "tạo nhắc nhở"]) and not any(phrase in command for phrase in ["xóa", "hủy"]):
        # Tách nội dung và thời gian
        content_parts = []
        time_str = ""
        
        # Tìm mẫu thời gian trong chuỗi trước
        import re
        time_patterns = [
            r'\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?',  # DD/MM/YYYY, DD-MM-YYYY
            r'\d{1,2}\s*(?:h|giờ)(?:\s*\d{1,2})?',  # 8h, 8 giờ, 8h30, 8 giờ 30
            r'\d{1,2}:\d{1,2}'  # 8:30
        ]
        
        match = None
        for pattern in time_patterns:
            match = re.search(pattern, command)
            if match:
                break
        
        if match:
            time_index = match.start()
            content_parts.append(command[:time_index].strip())
            time_str = command[time_index:].strip()
        else:
            # Nếu không tìm thấy mẫu thời gian, tìm theo từ khóa
            time_keywords = ["vào lúc", "vào", "lúc", "ngày", "hôm nay", "ngày mai", "tuần sau"]
            for keyword in time_keywords:
                if keyword in command:
                    parts = command.split(keyword, 1)
                    content_parts.append(parts[0])
                    time_str = keyword + parts[1]
                    break
        
        # Nếu vẫn không tìm thấy thời gian
        if not time_str:
            return "Vui lòng cung cấp thời gian cho nhắc nhở. Ví dụ: 'nhắc tôi họp vào 14h ngày mai'."
        
        # Xử lý nội dung nhắc nhở
        content = "".join(content_parts)
        for prefix in ["nhắc tôi", "nhắc nhở", "thêm nhắc nhở", "tạo nhắc nhở", "xóa nhắc nhở", "hủy nhắc nhở"]:
            content = content.replace(prefix, "").strip()
        
        # Tách tiêu đề và mô tả
        title_parts = content.split(",", 1)
        title = title_parts[0].strip()
        description = title_parts[1].strip() if len(title_parts) > 1 else ""
        
        # Thêm nhắc nhở
        return manager.add_reminder(title, time_str, description)
    
    # Xử lý lệnh xem danh sách nhắc nhở
    elif any(phrase in command for phrase in ["xem nhắc nhở", "xem lịch", "danh sách nhắc nhở", "lịch", "sự kiện"]):
        # Xác định bộ lọc
        filter_str = None
        for keyword in ["hôm nay", "ngày mai", "tuần này", "tháng này"]:
            if keyword in command:
                filter_str = keyword
                break
                
        # Xử lý các câu hỏi về sự kiện
        if "có những" in command or "có gì" in command or "có sự kiện" in command:
            if "ngày mai" in command:
                filter_str = "ngày mai"
            elif "hôm nay" in command:
                filter_str = "hôm nay"
            elif "tuần này" in command:
                filter_str = "tuần này"
            elif "tháng này" in command:
                filter_str = "tháng này"
        
        return manager.list_reminders(filter_str)
    
    # Xử lý lệnh xem danh sách nhắc nhở
    
    # Mặc định hiển thị hướng dẫn
    return "Tính năng nhắc nhở:\n- Thêm: 'nhắc tôi <nội dung> vào <thời gian>'\n- Xem: 'xem nhắc nhở', 'lịch hôm nay', 'có sự kiện gì ngày mai?'\n- Xóa: 'xóa nhắc nhở id:<id>' hoặc 'xóa ghi chú <nội dung>'"