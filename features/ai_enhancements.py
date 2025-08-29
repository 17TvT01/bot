import json
import os
import datetime
import threading
from collections import defaultdict
from typing import Dict, List, Tuple
import pickle

class AIAssistant:
    def __init__(self):
        self.data_file = "assistant_data.pkl"
        self.user_data = {}
        self.needs_saving = False
        self._data_loaded = False
        
        # Tải dữ liệu cơ bản ngay lập tức
        self._load_minimal_data()
        
        # Tải dữ liệu đầy đủ trong background
        threading.Thread(target=self._load_full_data, daemon=True).start()

    def _load_minimal_data(self):
        """Tải dữ liệu tối thiểu cần thiết cho khởi động nhanh."""
        # Tạo cấu trúc dữ liệu cơ bản
        self.user_data = {
            'usage_patterns': {},
            'time_based_patterns': {},
            'preferences': {},
            'command_history': [],
            'success_rate': {}
        }
    
    def _load_full_data(self):
        """Tải toàn bộ dữ liệu trong background."""
        try:
            if os.path.exists(self.data_file):
                try:
                    with open(self.data_file, 'rb') as f:
                        data = pickle.load(f)
                    # Basic validation
                    if isinstance(data, dict):
                        self.user_data = data
                        print("AI data loaded successfully")
                except (pickle.UnpicklingError, EOFError, TypeError) as e:
                    print(f"Error loading AI data: {e}")
                    # If file is corrupted or not a dict, create new data
                    self.user_data = self._create_default_data()
            else:
                self.user_data = self._create_default_data()
        finally:
            self._data_loaded = True
            
    def _load_data(self) -> Dict:
        """Legacy method for backward compatibility."""
        if self._data_loaded:
            return self.user_data
        return self._create_default_data()

    def _create_default_data(self) -> Dict:
        """Create default data structure."""
        return {
            'usage_patterns': defaultdict(int),
            'time_based_patterns': defaultdict(lambda: defaultdict(int)),
            'preferences': {},
            'command_history': [],
            'success_rate': defaultdict(float)
        }

    def _save_data(self):
        """Save user data to file if changes have been made."""
        if self.needs_saving:
            # Convert defaultdicts to regular dicts for pickling
            data_to_save = dict(self.user_data)
            data_to_save['usage_patterns'] = dict(self.user_data.get('usage_patterns', {}))
            data_to_save['time_based_patterns'] = {k: dict(v) for k, v in self.user_data.get('time_based_patterns', {}).items()}
            data_to_save['success_rate'] = dict(self.user_data.get('success_rate', {}))

            with open(self.data_file, 'wb') as f:
                pickle.dump(data_to_save, f)
            self.needs_saving = False

    def record_command(self, command: str, success: bool = True):
        """Record a command and its success status without immediate saving."""
        try:
            # Đảm bảo các cấu trúc dữ liệu cần thiết đã được khởi tạo
            if 'command_history' not in self.user_data:
                self.user_data['command_history'] = []
            if 'usage_patterns' not in self.user_data:
                self.user_data['usage_patterns'] = {}
            if 'time_based_patterns' not in self.user_data:
                self.user_data['time_based_patterns'] = {}
            if 'success_rate' not in self.user_data:
                self.user_data['success_rate'] = {}
            
            # Store command in history (keep last 100 commands)
            self.user_data['command_history'].append({
                'command': command,
                'timestamp': datetime.datetime.now().isoformat(),
                'success': success
            })
            self.user_data['command_history'] = self.user_data['command_history'][-100:]

            # Update usage patterns - sử dụng defaultdict để tránh lỗi
            if command not in self.user_data['usage_patterns']:
                self.user_data['usage_patterns'][command] = 0
            self.user_data['usage_patterns'][command] += 1

            # Update time-based patterns
            current_hour = datetime.datetime.now().hour
            time_category = self._get_time_category(current_hour)
            
            # Đảm bảo time_based_patterns có cấu trúc đúng
            if time_category not in self.user_data['time_based_patterns']:
                self.user_data['time_based_patterns'][time_category] = {}
            if command not in self.user_data['time_based_patterns'][time_category]:
                self.user_data['time_based_patterns'][time_category][command] = 0
                
            self.user_data['time_based_patterns'][time_category][command] += 1

            # Update success rate
            if command in self.user_data['success_rate']:
                current_rate = self.user_data['success_rate'][command]
                new_rate = (current_rate * 0.7) + (1.0 if success else 0.0) * 0.3
                self.user_data['success_rate'][command] = new_rate
            else:
                self.user_data['success_rate'][command] = 1.0 if success else 0.0
            
            self.needs_saving = True
        except Exception as e:
            print(f"DEBUG: Error in record_command: {e}")
            # Không gây lỗi cho chương trình chính
    
    def _get_time_category(self, hour: int) -> str:
        """Categorize time into periods."""
        if 5 <= hour < 12:
            return "morning"
        elif 12 <= hour < 18:
            return "afternoon"
        elif 18 <= hour < 22:
            return "evening"
        else:
            return "night"
    
    def predict_command(self, partial_command: str = "") -> List[Tuple[str, float]]:
        """Predict likely commands based on history and context with improved scoring."""
        predictions = []
        
        # Check if data is fully loaded before proceeding
        if not self._data_loaded:
            return []
            
        try:
            current_hour = datetime.datetime.now().hour
            time_category = self._get_time_category(current_hour)
            
            # Normalize partial command for better matching
            normalized_partial = partial_command.lower().strip()
            
            # Based on usage frequency (higher weight for exact matches)
            for cmd, count in self.user_data.get('usage_patterns', {}).items():
                normalized_cmd = cmd.lower()
                
                # Exact match gets highest score
                if normalized_partial == normalized_cmd:
                    score = 1.0
                # Partial match
                elif normalized_partial in normalized_cmd:
                    # Calculate score based on match position and frequency
                    position_score = 1.0 - (normalized_cmd.find(normalized_partial) / max(1, len(normalized_cmd)))
                    frequency_score = count / max(1, sum(self.user_data['usage_patterns'].values()))
                    score = (position_score * 0.6) + (frequency_score * 0.4)
                else:
                    continue
                    
                predictions.append((cmd, score))
            
            # Based on time of day patterns
            time_commands = self.user_data.get('time_based_patterns', {}).get(time_category, {})
            for cmd, count in time_commands.items():
                normalized_cmd = cmd.lower()
                
                if normalized_partial in normalized_cmd:
                    total_time_commands = sum(time_commands.values())
                    time_score = count / max(1, total_time_commands) * 0.7
                    
                    # Add to existing prediction or create new one
                    existing_pred = next((p for p in predictions if p[0] == cmd), None)
                    if existing_pred:
                        existing_score = existing_pred[1]
                        predictions.remove(existing_pred)
                        predictions.append((cmd, max(existing_score, time_score)))
                    else:
                        predictions.append((cmd, time_score))
            
            # Sort by score and remove duplicates
            predictions.sort(key=lambda x: x[1], reverse=True)
            seen = set()
            unique_predictions = []
            for cmd, score in predictions:
                if cmd not in seen and score > 0.1:  # Minimum threshold
                    seen.add(cmd)
                    unique_predictions.append((cmd, score))
            
            return unique_predictions[:3]  # Return top 3 most relevant predictions
        except Exception as e:
            print(f"DEBUG: Error in predict_command: {e}")
            return []
    
    def get_smart_suggestions(self) -> List[str]:
        """Context-aware suggestions (time, usage, reminders), scored and de-duplicated."""
        if not self._data_loaded:
            return ["xem thoi tiet", "mo may tinh", "xem thong tin he thong"]

        try:
            now = datetime.datetime.now()
            hour = now.hour
            recent = [c['command'] for c in self.user_data.get('command_history', [])[-10:] if c.get('success')]
            joined_recent = " ".join(recent).lower()

            candidates: List[Tuple[str, float]] = []

            def add(text: str, score: float):
                if text:
                    candidates.append((text, score))

            # Time-based
            if 6 <= hour < 9:
                add("xem lich hom nay", 0.7)
            if 11 <= hour < 13:
                add("dat bao thuc luc 14h", 0.6)
            if 16 <= hour < 20:
                add("xem thoi tiet ngay mai", 0.6)

            # Usage-based
            if any(w in joined_recent for w in ["thoi tiet", "weather"]):
                add("theo doi thoi tiet hang ngay", 0.65)
            if any(w in joined_recent for w in ["tinh", "cong", "tru", "nhan", "chia", "calculator"]):
                add("mo may tinh de tinh nhanh", 0.55)
            if any(w in joined_recent for w in ["he thong", "system", "cpu", "ram"]):
                add("xem thong tin he thong", 0.5)

            # Reminder-aware
            try:
                from features.reminder import get_reminder_manager
                rm = get_reminder_manager()
                upcoming = []
                for r in getattr(rm, 'reminders', []) or []:
                    t = r.get('time')
                    if hasattr(t, 'strftime'):
                        dt = t
                    else:
                        try:
                            dt = datetime.datetime.fromisoformat(str(t))
                        except Exception:
                            dt = None
                    if dt and dt >= now and (dt - now).total_seconds() <= 60*60*8:
                        upcoming.append((r, dt))
                if upcoming:
                    upcoming.sort(key=lambda x: x[1])
                    r, dt = upcoming[0]
                    hhmm = dt.strftime("%Hh%M").replace("h00", "h")
                    add("xem danh sach su kien hom nay", 0.8)
                    add(f"nhac toi '{r.get('title','cuoc hop')}' luc {hhmm}", 0.75)
            except Exception:
                pass

            # Promote frequent commands
            usage = self.user_data.get('usage_patterns', {}) or {}
            total = sum(usage.values()) or 1
            for cmd, cnt in usage.items():
                frac = cnt / total
                if frac > 0.1:
                    add(cmd, 0.3 + min(0.5, frac))

            # Adjust by success rate
            success_rate = self.user_data.get('success_rate', {}) or {}
            scored: List[Tuple[str, float]] = []
            for text, base in candidates:
                sr = success_rate.get(text, 0.6)
                scored.append((text, base * (0.6 + 0.4 * sr)))

            # Sort, dedup, limit 3
            scored.sort(key=lambda x: x[1], reverse=True)
            seen = set()
            out: List[str] = []
            for text, _ in scored:
                k = text.strip().lower()
                if k and k not in seen:
                    seen.add(k)
                    out.append(text)
                if len(out) >= 3:
                    break
            return out
        except Exception as e:
            print(f"DEBUG: Error in get_smart_suggestions: {e}")
            return ["xem thoi tiet", "mo may tinh", "xem thong tin he thong"]
    def learn_preference(self, feature: str, preference: str, value: any):
        """Learn user preferences for specific features."""
        if 'preferences' not in self.user_data:
            self.user_data['preferences'] = {}
        if feature not in self.user_data['preferences']:
            self.user_data['preferences'][feature] = {}
        self.user_data['preferences'][feature][preference] = value
        self._save_data()
    
    def get_preference(self, feature: str, preference: str, default: any = None) -> any:
        """Get user preference for a specific feature."""
        return self.user_data.get('preferences', {}).get(feature, {}).get(preference, default)

# --- Lazy-loaded singleton pattern ---
_ai_assistant_instance = None

def get_ai_assistant():
    """Get a single, lazy-loaded instance of the AI Assistant."""
    global _ai_assistant_instance
    if _ai_assistant_instance is None:
        _ai_assistant_instance = AIAssistant()
    return _ai_assistant_instance
# ------------------------------------

def enhance_with_ai(response: str, command: str, success: bool = True) -> str:
    """Enhance response with AI capabilities."""
    try:
        # Kiểm tra command có phải là string không
        if not isinstance(command, str):
            print(f"DEBUG: Command is not a string: {type(command)}")
            return response
            
        ai_assistant = get_ai_assistant()
        
        # Ghi lại lệnh trong một thread riêng để không làm chậm phản hồi
        def record_in_background():
            try:
                ai_assistant.record_command(command, success)
            except Exception as e:
                print(f"DEBUG: Error recording command: {e}")
        
        threading.Thread(target=record_in_background, daemon=True).start()
        
        # Add smart suggestions if response was successful
        # Chỉ thêm gợi ý nếu dữ liệu đã được tải đầy đủ
        if success and ai_assistant._data_loaded:
            suggestions = ai_assistant.get_smart_suggestions()
            if suggestions:
                response += "\n\n💡 Gợi ý thông minh:\n" + "\n".join(f"• {s}" for s in suggestions)
    except Exception as e:
        print(f"DEBUG: Error in enhance_with_ai: {e}")
        # Không thay đổi response khi có lỗi
    
    return response

def get_ai_predictions(partial_command: str = "") -> List[str]:
    """Get AI predictions for auto-complete."""
    ai_assistant = get_ai_assistant()
    
    # Nếu dữ liệu chưa được tải đầy đủ, trả về danh sách trống
    if not ai_assistant._data_loaded:
        return []
        
    try:
        predictions = ai_assistant.predict_command(partial_command)
        return [cmd for cmd, score in predictions if score > 0.1]
    except Exception as e:
        print(f"DEBUG: Error in get_ai_predictions: {e}")
        return []

# Keywords and patterns for feature detection
keywords = ["ai", "trí tuệ nhân tạo", "học máy", "dự đoán", "gợi ý"]
patterns = [
    "gợi ý cho tôi",
    "dự đoán lệnh",
    "học từ tôi"
]

def ai_assistant_feature(command: str = None) -> str:
    """AI assistant main feature."""
    if command and "dự đoán" in command:
        predictions = get_ai_predictions()
        if predictions:
            return "Dự đoán lệnh:\n" + "\n".join(f"• {p}" for p in predictions[:3])
        else:
            return "Chưa có đủ dữ liệu để dự đoán. Hãy sử dụng trợ lý nhiều hơn!"
    
    return "Tính năng AI đã được kích hoạt. Tôi sẽ học hỏi từ bạn và đưa ra gợi ý thông minh!"
