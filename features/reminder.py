import datetime
import json
import os
import re
import threading
import time
from typing import Dict, List, Optional, Tuple

# ÄÆ°á»ng dáº«n Ä‘áº¿n tá»‡p lÆ°u trá»¯ dá»¯ liá»‡u nháº¯c nhá»Ÿ
REMINDER_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "reminder_data.json")

# Tá»« khÃ³a vÃ  máº«u cho viá»‡c nháº­n diá»‡n tÃ­nh nÄƒng
keywords = ["nháº¯c nhá»Ÿ", "lá»‹ch", "sá»± kiá»‡n", "háº¹n", "lá»‹ch trÃ¬nh", "reminder", "calendar", "event", "ghi chÃº"]

patterns = [
    "nháº¯c tÃ´i",
    "thÃªm nháº¯c nhá»Ÿ",
    "táº¡o nháº¯c nhá»Ÿ",
    "lá»‹ch hÃ´m nay",
    "lá»‹ch ngÃ y mai",
    "lá»‹ch tuáº§n nÃ y",
    "lá»‹ch thÃ¡ng nÃ y",
    "xem lá»‹ch",
    "xem nháº¯c nhá»Ÿ",
    "xÃ³a nháº¯c nhá»Ÿ",
    "há»§y nháº¯c nhá»Ÿ",
    "xÃ³a ghi chÃº",
    "há»§y ghi chÃº",
    "xÃ³a sá»± kiá»‡n",
    "há»§y sá»± kiá»‡n",
    "cÃ³ sá»± kiá»‡n gÃ¬",
    "cÃ³ lá»‹ch gÃ¬",
    "cÃ³ ghi chÃº gÃ¬"
]

class ReminderManager:
    """Quáº£n lÃ½ cÃ¡c nháº¯c nhá»Ÿ vÃ  sá»± kiá»‡n trong lá»‹ch"""
    
    def __init__(self):
        self.reminders = []
        self.active_reminders = {}
        self.reminder_lock = threading.Lock()
        self.load_reminders()
        self.start_reminder_thread()
    
    def load_reminders(self) -> None:
        """Táº£i dá»¯ liá»‡u nháº¯c nhá»Ÿ tá»« tá»‡p"""
        try:
            if os.path.exists(REMINDER_FILE):
                with open(REMINDER_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.reminders = data.get('reminders', [])
                    
                    # Chuyá»ƒn Ä‘á»•i chuá»—i thá»i gian thÃ nh Ä‘á»‘i tÆ°á»£ng datetime
                    for reminder in self.reminders:
                        # Chuyá»ƒn Ä‘á»•i táº¥t cáº£ cÃ¡c trÆ°á»ng datetime
                        for key, value in reminder.items():
                            if isinstance(value, str) and key in ['time', 'created']:
                                try:
                                    reminder[key] = datetime.datetime.fromisoformat(value)
                                except ValueError:
                                    # Náº¿u khÃ´ng thá»ƒ chuyá»ƒn Ä‘á»•i, giá»¯ nguyÃªn giÃ¡ trá»‹ chuá»—i
                                    pass
        except Exception as e:
            print(f"Lá»—i khi táº£i dá»¯ liá»‡u nháº¯c nhá»Ÿ: {e}")
            self.reminders = []
    
    def save_reminders(self) -> None:
        """LÆ°u dá»¯ liá»‡u nháº¯c nhá»Ÿ vÃ o tá»‡p"""
        try:
            # Chuyá»ƒn Ä‘á»•i Ä‘á»‘i tÆ°á»£ng datetime thÃ nh chuá»—i trÆ°á»›c khi lÆ°u
            serializable_reminders = []
            for reminder in self.reminders:
                reminder_copy = reminder.copy()
                # Chuyá»ƒn Ä‘á»•i táº¥t cáº£ cÃ¡c trÆ°á»ng datetime thÃ nh chuá»—i
                for key, value in reminder_copy.items():
                    if isinstance(value, datetime.datetime):
                        reminder_copy[key] = value.isoformat()
                serializable_reminders.append(reminder_copy)
                
            with open(REMINDER_FILE, 'w', encoding='utf-8') as f:
                json.dump({'reminders': serializable_reminders}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Lá»—i khi lÆ°u dá»¯ liá»‡u nháº¯c nhá»Ÿ: {e}")
    
    def add_reminder(self, title: str, time_str: str, description: str = "") -> str:
        """ThÃªm má»™t nháº¯c nhá»Ÿ má»›i"""
        try:
            # PhÃ¢n tÃ­ch chuá»—i thá»i gian
            reminder_time = self._parse_time(time_str)
            if not reminder_time:
                return "KhÃ´ng thá»ƒ nháº­n dáº¡ng thá»i gian. Vui lÃ²ng sá»­ dá»¥ng Ä‘á»‹nh dáº¡ng nhÆ° 'ngÃ y mai 8h', '15/05/2023 14:30'."
            
            # Táº¡o ID duy nháº¥t cho nháº¯c nhá»Ÿ
            reminder_id = str(int(time.time()))
            
            # Táº¡o nháº¯c nhá»Ÿ má»›i
            reminder = {
                'id': reminder_id,
                'title': title,
                'description': description,
                'time': reminder_time,
                'created': datetime.datetime.now()
            }
            
            # ThÃªm vÃ o danh sÃ¡ch vÃ  lÆ°u
            with self.reminder_lock:
                self.reminders.append(reminder)
                self.save_reminders()
                
                # Náº¿u nháº¯c nhá»Ÿ trong tÆ°Æ¡ng lai, thÃªm vÃ o danh sÃ¡ch theo dÃµi
                if reminder_time > datetime.datetime.now():
                    self._schedule_reminder(reminder)
            
            # Äá»‹nh dáº¡ng thá»i gian Ä‘á»ƒ hiá»ƒn thá»‹
            time_display = reminder_time.strftime("%H:%M ngÃ y %d/%m/%Y")
            return f"ÄÃ£ thÃªm nháº¯c nhá»Ÿ: {title} vÃ o lÃºc {time_display}"
            
        except Exception as e:
            return f"Lá»—i khi thÃªm nháº¯c nhá»Ÿ: {str(e)}"
    
    def _parse_time(self, time_str: str) -> Optional[datetime.datetime]:
        """PhÃ¢n tÃ­ch chuá»—i thá»i gian thÃ nh Ä‘á»‘i tÆ°á»£ng datetime"""
        now = datetime.datetime.now()
        time_str = time_str.lower()
        
        try:
            # Xá»­ lÃ½ cÃ¡c tá»« khÃ³a thá»i gian tÆ°Æ¡ng Ä‘á»‘i
            if "hÃ´m nay" in time_str or "today" in time_str:
                date = now.date()
            elif "ngÃ y mai" in time_str or "tomorrow" in time_str:
                date = (now + datetime.timedelta(days=1)).date()
            elif "tuáº§n sau" in time_str or "next week" in time_str:
                date = (now + datetime.timedelta(days=7)).date()
            else:
                # Thá»­ phÃ¢n tÃ­ch ngÃ y thÃ¡ng tá»« chuá»—i
                # Há»— trá»£ cÃ¡c Ä‘á»‹nh dáº¡ng: DD/MM/YYYY, DD-MM-YYYY
                date_match = None
                for pattern in [r'(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?', r'(\d{1,2}) thÃ¡ng (\d{1,2})(?: nÄƒm (\d{2,4}))?']:
                    match = re.search(pattern, time_str)
                    if match:
                        date_match = match
                        break
                
                if date_match:
                    day = int(date_match.group(1))
                    month = int(date_match.group(2))
                    year = int(date_match.group(3)) if date_match.group(3) else now.year
                    
                    # Xá»­ lÃ½ nÄƒm 2 chá»¯ sá»‘
                    if year < 100:
                        year += 2000
                        
                    date = datetime.date(year, month, day)
                else:
                    date = now.date()
            
            # Xá»­ lÃ½ giá»
            hour, minute = 8, 0  # Máº·c Ä‘á»‹nh 8:00 sÃ¡ng
            
            # TÃ¬m giá» trong chuá»—i
            hour_match = re.search(r'(\d{1,2})[:](\d{1,2})', time_str)
            if hour_match:
                hour = int(hour_match.group(1))
                minute = int(hour_match.group(2))
            else:
                # TÃ¬m giá» dáº¡ng "8h", "14 giá»", "15h30"
                hour_match = re.search(r'(\d{1,2})\s*(?:h|giá»)\s*(\d{1,2})?', time_str)
                if hour_match:
                    hour = int(hour_match.group(1))
                    minute = int(hour_match.group(2)) if hour_match.group(2) else 0
            
            # Táº¡o Ä‘á»‘i tÆ°á»£ng datetime
            reminder_time = datetime.datetime.combine(date, datetime.time(hour, minute))
            
            # Náº¿u thá»i gian Ä‘Ã£ qua trong ngÃ y hÃ´m nay, Ä‘áº·t vÃ o ngÃ y mai
            if reminder_time < now and "hÃ´m nay" in time_str:
                reminder_time += datetime.timedelta(days=1)
                
            return reminder_time
            
        except Exception as e:
            print(f"Lá»—i khi phÃ¢n tÃ­ch thá»i gian: {e}")
            return None
    
    def list_reminders(self, filter_str: str = None) -> str:
        """Liá»‡t kÃª cÃ¡c nháº¯c nhá»Ÿ"""
        with self.reminder_lock:
            if not self.reminders:
                return "Báº¡n chÆ°a cÃ³ nháº¯c nhá»Ÿ nÃ o."
            
            # Lá»c nháº¯c nhá»Ÿ náº¿u cÃ³ yÃªu cáº§u
            filtered_reminders = self.reminders
            if filter_str:
                filter_str = filter_str.lower()
                if "hÃ´m nay" in filter_str or "today" in filter_str:
                    today = datetime.datetime.now().date()
                    filtered_reminders = [r for r in self.reminders 
                                         if isinstance(r.get('time'), datetime.datetime) 
                                         and r['time'].date() == today]
                elif "ngÃ y mai" in filter_str or "tomorrow" in filter_str:
                    tomorrow = (datetime.datetime.now() + datetime.timedelta(days=1)).date()
                    filtered_reminders = [r for r in self.reminders 
                                         if isinstance(r.get('time'), datetime.datetime) 
                                         and r['time'].date() == tomorrow]
                elif "tuáº§n nÃ y" in filter_str or "this week" in filter_str:
                    today = datetime.datetime.now().date()
                    end_of_week = today + datetime.timedelta(days=(6 - today.weekday()))
                    filtered_reminders = [r for r in self.reminders 
                                         if isinstance(r.get('time'), datetime.datetime) 
                                         and today <= r['time'].date() <= end_of_week]
                else:
                    # Lá»c theo tá»« khÃ³a trong tiÃªu Ä‘á» hoáº·c mÃ´ táº£
                    filtered_reminders = [r for r in self.reminders 
                                         if filter_str in r['title'].lower() 
                                         or filter_str in r.get('description', '').lower()]
            
            # Sáº¯p xáº¿p theo thá»i gian
            filtered_reminders.sort(key=lambda x: x['time'] if isinstance(x.get('time'), datetime.datetime) else datetime.datetime.max)
            
            # Táº¡o danh sÃ¡ch hiá»ƒn thá»‹
            if not filtered_reminders:
                return "KhÃ´ng tÃ¬m tháº¥y nháº¯c nhá»Ÿ nÃ o phÃ¹ há»£p vá»›i yÃªu cáº§u."
                
            result = "ðŸ“… Danh sÃ¡ch nháº¯c nhá»Ÿ:\n\n"
            for i, reminder in enumerate(filtered_reminders, 1):
                time_str = reminder['time'].strftime("%H:%M ngÃ y %d/%m/%Y") if isinstance(reminder.get('time'), datetime.datetime) else "KhÃ´ng xÃ¡c Ä‘á»‹nh"
                desc = f" - {reminder['description']}" if reminder.get('description') else ""
                result += f"{i}. {reminder['title']} ({time_str}){desc} [ID: {reminder['id']}]\n"
                
            return result
    
    def delete_reminder(self, reminder_id: str) -> str:
        """XÃ³a má»™t nháº¯c nhá»Ÿ theo ID"""
        with self.reminder_lock:
            # TÃ¬m nháº¯c nhá»Ÿ theo ID
            for i, reminder in enumerate(self.reminders):
                if reminder['id'] == reminder_id:
                    # XÃ³a khá»i danh sÃ¡ch vÃ  lÆ°u
                    removed = self.reminders.pop(i)
                    self.save_reminders()
                    
                    # XÃ³a khá»i danh sÃ¡ch theo dÃµi náº¿u cÃ³
                    if reminder_id in self.active_reminders:
                        self.active_reminders.pop(reminder_id)
                        
                    return f"ÄÃ£ xÃ³a nháº¯c nhá»Ÿ: {removed['title']}"
            
            return "KhÃ´ng tÃ¬m tháº¥y nháº¯c nhá»Ÿ vá»›i ID Ä‘Ã£ cung cáº¥p."
    
    def _schedule_reminder(self, reminder: Dict) -> None:
        """LÃªn lá»‹ch cho má»™t nháº¯c nhá»Ÿ"""
        reminder_id = reminder['id']
        reminder_time = reminder['time']
        
        # TÃ­nh thá»i gian chá» (giÃ¢y)
        now = datetime.datetime.now()
        wait_seconds = (reminder_time - now).total_seconds()
        
        if wait_seconds <= 0:
            return
        
        # Táº¡o timer Ä‘á»ƒ kÃ­ch hoáº¡t nháº¯c nhá»Ÿ
        timer = threading.Timer(wait_seconds, self._trigger_reminder, args=[reminder_id])
        timer.daemon = True
        timer.start()
        
        # LÆ°u timer Ä‘á»ƒ cÃ³ thá»ƒ há»§y náº¿u cáº§n
        self.active_reminders[reminder_id] = timer
    
    def _trigger_reminder(self, reminder_id: str) -> None:
        """KÃ­ch hoáº¡t má»™t nháº¯c nhá»Ÿ"""
        with self.reminder_lock:
            # TÃ¬m nháº¯c nhá»Ÿ theo ID
            reminder = None
            for r in self.reminders:
                if r['id'] == reminder_id:
                    reminder = r
                    break
            
            if not reminder:
                return
            
            # XÃ³a khá»i danh sÃ¡ch theo dÃµi
            if reminder_id in self.active_reminders:
                self.active_reminders.pop(reminder_id)
            
            # Gá»­i thÃ´ng bÃ¡o
            self._send_notification(reminder)
    
    def _send_notification(self, reminder: Dict) -> None:
        """Gá»­i thÃ´ng bÃ¡o nháº¯c nhá»Ÿ"""
        # ÄÃ¢y lÃ  nÆ¡i Ä‘á»ƒ tÃ­ch há»£p vá»›i há»‡ thá»‘ng thÃ´ng bÃ¡o
        # Trong phiÃªn báº£n Ä‘Æ¡n giáº£n, chá»‰ in ra console
        print(f"\n[NHáº®C NHá»ž] {reminder['title']}")
        if reminder.get('description'):
            print(f"Chi tiáº¿t: {reminder['description']}")
        
        # ThÃªm code Ä‘á»ƒ hiá»ƒn thá»‹ thÃ´ng bÃ¡o trÃªn GUI á»Ÿ Ä‘Ã¢y
        # Sáº½ Ä‘Æ°á»£c tÃ­ch há»£p sau khi cáº­p nháº­t GUI
    
    def start_reminder_thread(self) -> None:
        """Khá»Ÿi Ä‘á»™ng thread theo dÃµi cÃ¡c nháº¯c nhá»Ÿ"""
        def _monitor_reminders():
            while True:
                try:
                    # LÃªn lá»‹ch láº¡i cÃ¡c nháº¯c nhá»Ÿ chÆ°a kÃ­ch hoáº¡t
                    with self.reminder_lock:
                        now = datetime.datetime.now()
                        for reminder in self.reminders:
                            reminder_id = reminder['id']
                            reminder_time = reminder.get('time')
                            
                            # Bá» qua náº¿u khÃ´ng pháº£i datetime hoáº·c Ä‘Ã£ qua
                            if not isinstance(reminder_time, datetime.datetime) or reminder_time < now:
                                continue
                                
                            # Náº¿u chÆ°a Ä‘Æ°á»£c lÃªn lá»‹ch, thÃªm vÃ o
                            if reminder_id not in self.active_reminders:
                                self._schedule_reminder(reminder)
                                
                except Exception as e:
                    print(f"Lá»—i trong thread nháº¯c nhá»Ÿ: {e}")
                    
                # Kiá»ƒm tra má»—i 60 giÃ¢y
                time.sleep(60)
        
        # Khá»Ÿi Ä‘á»™ng thread
        monitor_thread = threading.Thread(target=_monitor_reminders, daemon=True)
        monitor_thread.start()

# Singleton instance
_reminder_manager = None

def get_reminder_manager() -> ReminderManager:
    """Láº¥y instance cá»§a ReminderManager (singleton)"""
    global _reminder_manager
    if _reminder_manager is None:
        _reminder_manager = ReminderManager()
    return _reminder_manager

def reminder(command: str = None) -> str:
    """HÃ m chÃ­nh xá»­ lÃ½ cÃ¡c lá»‡nh liÃªn quan Ä‘áº¿n nháº¯c nhá»Ÿ"""
    if not command:
        return "TÃ­nh nÄƒng nháº¯c nhá»Ÿ giÃºp báº¡n quáº£n lÃ½ lá»‹ch vÃ  sá»± kiá»‡n. Sá»­ dá»¥ng 'nháº¯c tÃ´i <ná»™i dung> vÃ o <thá»i gian>' Ä‘á»ƒ táº¡o nháº¯c nhá»Ÿ má»›i."
    
    manager = get_reminder_manager()
    command = command.lower()
    
    # Xá»­ lÃ½ lá»‡nh xÃ³a nháº¯c nhá»Ÿ - Kiá»ƒm tra trÆ°á»›c Ä‘á»ƒ trÃ¡nh xung Ä‘á»™t vá»›i cÃ¡c tá»« khÃ³a khÃ¡c
    if any(phrase in command for phrase in ["xÃ³a nháº¯c", "xÃ³a nháº¯c nhá»Ÿ", "há»§y nháº¯c", "há»§y nháº¯c nhá»Ÿ", "xÃ³a lá»‹ch", "xÃ³a ghi chÃº", "xÃ³a sá»± kiá»‡n", "há»§y ghi chÃº", "há»§y sá»± kiá»‡n", "há»§y lá»‹ch"]):
        # TÃ¬m ID nháº¯c nhá»Ÿ
        import re
        id_match = re.search(r'id[:\s]*(\d+)', command, re.IGNORECASE)
        
        # TÃ¬m theo thá»i gian trong lá»‡nh
        time_match = None
        time_patterns = [
            r'(\d{1,2})[\s]*(?:h|giá»)(?:[\s]*(\d{1,2}))?',  # 8h, 8 giá», 8h30, 8 giá» 30
            r'(\d{1,2}):(\d{1,2})'  # 8:30
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, command)
            if match:
                time_match = match
                break
        
        # Kiá»ƒm tra tá»« khÃ³a thá»i gian
        time_filter = None
        if "ngÃ y mai" in command:
            time_filter = "ngÃ y mai"
        elif "hÃ´m nay" in command:
            time_filter = "hÃ´m nay"
        
        # Náº¿u cÃ³ thÃ´ng tin vá» thá»i gian, tÃ¬m nháº¯c nhá»Ÿ theo thá»i gian
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
                    
                    # Kiá»ƒm tra ngÃ y
                    matches_day = True
                    if time_filter == "ngÃ y mai" and reminder_time.date() != tomorrow.date():
                        matches_day = False
                    elif time_filter == "hÃ´m nay" and reminder_time.date() != now.date():
                        matches_day = False
                    
                    # Kiá»ƒm tra giá» náº¿u cÃ³
                    matches_hour = True
                    if hour is not None and reminder_time.hour != hour:
                        matches_hour = False
                    
                    # Náº¿u khá»›p cáº£ ngÃ y vÃ  giá»
                    if matches_day and matches_hour:
                        return manager.delete_reminder(reminder['id'])
                
                return "KhÃ´ng tÃ¬m tháº¥y nháº¯c nhá»Ÿ nÃ o phÃ¹ há»£p vá»›i thá»i gian Ä‘Ã£ chá»‰ Ä‘á»‹nh."
        
        # TÃ¬m theo tá»« khÃ³a trong tiÃªu Ä‘á»
        if not id_match:
            # TÃ¬m tá»« khÃ³a sau cÃ¡c tá»« nhÆ° "xÃ³a", "há»§y"
            keywords = ["xÃ³a", "há»§y"]
            title_keywords = None
            
            for keyword in keywords:
                if keyword in command:
                    parts = command.split(keyword, 1)
                    if len(parts) > 1:
                        title_keywords = parts[1].strip()
                        break
            
            if title_keywords:
                # Loáº¡i bá» cÃ¡c tá»« khÃ´ng cáº§n thiáº¿t
                for word in ["nháº¯c nhá»Ÿ", "ghi chÃº", "lá»‹ch", "sá»± kiá»‡n", "giÃºp", "tÃ´i", "cho", "cá»§a"]:
                    title_keywords = title_keywords.replace(word, "").strip()
                
                # TÃ¬m nháº¯c nhá»Ÿ cÃ³ tiÃªu Ä‘á» chá»©a tá»« khÃ³a
                if title_keywords:
                    with manager.reminder_lock:
                        for reminder in manager.reminders:
                            if title_keywords.lower() in reminder['title'].lower():
                                return manager.delete_reminder(reminder['id'])
                    
                    return f"KhÃ´ng tÃ¬m tháº¥y nháº¯c nhá»Ÿ nÃ o cÃ³ ná»™i dung '{title_keywords}'."
        
        if id_match:
            reminder_id = id_match.group(1)
            return manager.delete_reminder(reminder_id)
        else:
            # Hiá»ƒn thá»‹ danh sÃ¡ch nháº¯c nhá»Ÿ Ä‘á»ƒ ngÆ°á»i dÃ¹ng chá»n
            reminders_list = manager.list_reminders()
            return f"Vui lÃ²ng chá»‰ Ä‘á»‹nh nháº¯c nhá»Ÿ cáº§n xÃ³a báº±ng ID hoáº·c ná»™i dung cá»¥ thá»ƒ.\n\n{reminders_list}\n\nVÃ­ dá»¥: 'xÃ³a nháº¯c nhá»Ÿ id:1234' hoáº·c 'xÃ³a nháº¯c nhá»Ÿ cuá»™c há»p'."
    
    # Xá»­ lÃ½ lá»‡nh thÃªm nháº¯c nhá»Ÿ - chá»‰ xá»­ lÃ½ khi khÃ´ng pháº£i lÃ  lá»‡nh xÃ³a
    elif any(phrase in command for phrase in ["nháº¯c tÃ´i", "thÃªm nháº¯c nhá»Ÿ", "táº¡o nháº¯c nhá»Ÿ"]) and not any(phrase in command for phrase in ["xÃ³a", "há»§y"]):
        # TÃ¡ch ná»™i dung vÃ  thá»i gian
        content_parts = []
        time_str = ""
        
        # TÃ¬m máº«u thá»i gian trong chuá»—i trÆ°á»›c
        import re
        time_patterns = [
            r'\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?',  # DD/MM/YYYY, DD-MM-YYYY
            r'\d{1,2}\s*(?:h|giá»)(?:\s*\d{1,2})?',  # 8h, 8 giá», 8h30, 8 giá» 30
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
            # Náº¿u khÃ´ng tÃ¬m tháº¥y máº«u thá»i gian, tÃ¬m theo tá»« khÃ³a
            time_keywords = ["vÃ o lÃºc", "vÃ o", "lÃºc", "ngÃ y", "hÃ´m nay", "ngÃ y mai", "tuáº§n sau"]
            for keyword in time_keywords:
                if keyword in command:
                    parts = command.split(keyword, 1)
                    content_parts.append(parts[0])
                    time_str = keyword + parts[1]
                    break
        
        # Náº¿u váº«n khÃ´ng tÃ¬m tháº¥y thá»i gian
        if not time_str:
            return "Vui lÃ²ng cung cáº¥p thá»i gian cho nháº¯c nhá»Ÿ. VÃ­ dá»¥: 'nháº¯c tÃ´i há»p vÃ o 14h ngÃ y mai'."
        
        # Xá»­ lÃ½ ná»™i dung nháº¯c nhá»Ÿ
        content = "".join(content_parts)
        for prefix in ["nháº¯c tÃ´i", "nháº¯c nhá»Ÿ", "thÃªm nháº¯c nhá»Ÿ", "táº¡o nháº¯c nhá»Ÿ", "xÃ³a nháº¯c nhá»Ÿ", "há»§y nháº¯c nhá»Ÿ"]:
            content = content.replace(prefix, "").strip()
        
        # TÃ¡ch tiÃªu Ä‘á» vÃ  mÃ´ táº£
        title_parts = content.split(",", 1)
        title = title_parts[0].strip()
        description = title_parts[1].strip() if len(title_parts) > 1 else ""
        
        # ThÃªm nháº¯c nhá»Ÿ
        return manager.add_reminder(title, time_str, description)
    
    # Xá»­ lÃ½ lá»‡nh xem danh sÃ¡ch nháº¯c nhá»Ÿ
    elif any(phrase in command for phrase in ["xem nháº¯c nhá»Ÿ", "xem lá»‹ch", "danh sÃ¡ch nháº¯c nhá»Ÿ", "lá»‹ch", "sá»± kiá»‡n"]):
        # XÃ¡c Ä‘á»‹nh bá»™ lá»c
        filter_str = None
        for keyword in ["hÃ´m nay", "ngÃ y mai", "tuáº§n nÃ y", "thÃ¡ng nÃ y"]:
            if keyword in command:
                filter_str = keyword
                break
                
        # Xá»­ lÃ½ cÃ¡c cÃ¢u há»i vá» sá»± kiá»‡n
        if "cÃ³ nhá»¯ng" in command or "cÃ³ gÃ¬" in command or "cÃ³ sá»± kiá»‡n" in command:
            if "ngÃ y mai" in command:
                filter_str = "ngÃ y mai"
            elif "hÃ´m nay" in command:
                filter_str = "hÃ´m nay"
            elif "tuáº§n nÃ y" in command:
                filter_str = "tuáº§n nÃ y"
            elif "thÃ¡ng nÃ y" in command:
                filter_str = "thÃ¡ng nÃ y"
        
        return "[[PANEL:NOTES]]" + manager.list_reminders(filter_str)
    
    # Xá»­ lÃ½ lá»‡nh xem danh sÃ¡ch nháº¯c nhá»Ÿ
    
    # Máº·c Ä‘á»‹nh hiá»ƒn thá»‹ hÆ°á»›ng dáº«n
    return "TÃ­nh nÄƒng nháº¯c nhá»Ÿ:\n- ThÃªm: 'nháº¯c tÃ´i <ná»™i dung> vÃ o <thá»i gian>'\n- Xem: 'xem nháº¯c nhá»Ÿ', 'lá»‹ch hÃ´m nay', 'cÃ³ sá»± kiá»‡n gÃ¬ ngÃ y mai?'\n- XÃ³a: 'xÃ³a nháº¯c nhá»Ÿ id:<id>' hoáº·c 'xÃ³a ghi chÃº <ná»™i dung>'"

