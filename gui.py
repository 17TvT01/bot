import tkinter as tk
from tkinter import scrolledtext, messagebox
import threading
import time
import assistant
from features.ai_enhancements import get_ai_assistant, get_ai_predictions

# Lazy import for reminder feature
_reminder_manager = None
def get_reminder_manager():
    global _reminder_manager
    if _reminder_manager is None:
        try:
            from features.reminder import get_reminder_manager as get_rm
            _reminder_manager = get_rm()
        except ImportError:
            return None
    return _reminder_manager

class AssistantGUI:
    def __init__(self, root):
        self.root = root
        self.processing = False
        self.pending_commands = []
        
        # Đo thời gian khởi động
        self.start_time = time.time()
        
        # Pre-initialize minimal UI
        root.title("Trợ lý ảo - Tối ưu hóa")
        root.geometry("500x400")
        
        # Add shutdown hook
        root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Tạo toàn bộ giao diện ngay lập tức
        self._create_ui()
        
        # Hiển thị thông báo khởi động
        self._add_text("Trợ lý: Chào bạn! Đang khởi động...")
        
        # Cập nhật giao diện ngay lập tức
        self.root.update_idletasks()
        
        # Bắt đầu tải tính năng trong background
        self.root.after(10, self._start_loading_features)

    def on_closing(self):
        """Handle window closing event."""
        get_ai_assistant()._save_data()
        # Lưu dữ liệu nhắc nhở nếu có
        reminder_manager = get_reminder_manager()
        if reminder_manager:
            reminder_manager.save_reminders()
        self.root.destroy()

    def _create_ui(self):
        """Tạo toàn bộ giao diện người dùng ngay lập tức."""
        # Output area
        self.output_area = scrolledtext.ScrolledText(
            self.root, wrap=tk.WORD, width=60, height=18,
            state=tk.DISABLED, font=("Arial", 10)
        )
        self.output_area.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        # Status bar
        self.status_frame = tk.Frame(self.root)
        self.status_frame.pack(fill=tk.X, padx=10, pady=(0, 5))
        
        self.status_label = tk.Label(
            self.status_frame,
            text="🔄 Đang tải tính năng...",
            font=("Arial", 8),
            foreground="blue"
        )
        self.status_label.pack(side=tk.LEFT)
        
        # Input Frame
        self.input_frame = tk.Frame(self.root)
        self.input_frame.pack(padx=10, pady=(0, 10), fill=tk.X)

        self.input_entry = tk.Entry(
            self.input_frame,
            font=("Arial", 10),
            state=tk.DISABLED
        )
        self.input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5)
        
        self.send_button = tk.Button(
            self.input_frame,
            text="Gửi",
            command=self.process_input,
            state=tk.DISABLED
        )
        self.send_button.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Bind events
        self.input_entry.bind("<Return>", self.process_input)
        
        # Log UI creation time
        ui_time = time.time() - self.start_time
        print(f"UI created in: {ui_time:.2f} seconds")
    
    def _start_loading_features(self):
        """Bắt đầu tải tính năng trong background."""
        # Start background feature loading
        assistant.initialize_assistant()
        
        # Monitor loading progress
        self.monitor_feature_loading()
        
        # Khởi tạo hệ thống thông báo nhắc nhở
        self.root.after(1000, self._initialize_reminder_notifications)
    
    def _initialize_reminder_notifications(self):
        """Khởi tạo hệ thống thông báo nhắc nhở"""
        reminder_manager = get_reminder_manager()
        if reminder_manager:
            # Ghi đè phương thức _send_notification để hiển thị thông báo trên GUI
            original_send_notification = reminder_manager._send_notification
            
            def gui_notification(reminder):
                # Gọi phương thức gốc
                original_send_notification(reminder)
                
                # Hiển thị thông báo trên GUI
                self.show_reminder_notification(reminder)
            
            # Thay thế phương thức
            reminder_manager._send_notification = gui_notification
            
            print("Hệ thống thông báo nhắc nhở đã được khởi tạo")
    
    def show_reminder_notification(self, reminder):
        """Hiển thị thông báo nhắc nhở trên GUI"""
        title = reminder.get('title', 'Nhắc nhở')
        description = reminder.get('description', '')
        
        # Hiển thị thông báo trong output area
        notification_text = f"\n🔔 NHẮC NHỞ: {title}"
        if description:
            notification_text += f"\n   {description}"
        
        self._add_text(notification_text)
        
        # Hiển thị cửa sổ thông báo
        message = f"{title}"
        if description:
            message += f"\n\n{description}"
        
        # Sử dụng after để tránh chặn luồng chính
        self.root.after(100, lambda: messagebox.showinfo("Nhắc nhở", message))

    def monitor_feature_loading(self):
        """Monitor feature loading progress and update UI accordingly."""
        # Kiểm tra xem các tính năng cơ bản đã được tải chưa
        if hasattr(assistant, 'basic_features_loaded') and assistant.basic_features_loaded:
            # Nếu chưa kích hoạt giao diện nhập liệu
            if self.input_entry.cget('state') == 'disabled':
                self.status_label.config(
                    text="🟡 Tính năng cơ bản đã sẵn sàng, đang tải thêm...",
                    foreground="orange"
                )
                self.input_entry.config(state=tk.NORMAL)
                self.send_button.config(state=tk.NORMAL)
                self.input_entry.focus_set()
                self._add_text("Trợ lý: Tôi đã sẵn sàng với các tính năng cơ bản. Bạn có thể bắt đầu sử dụng.")
                
                # Tính thời gian để kích hoạt giao diện
                ready_time = time.time() - self.start_time
                print(f"UI ready for interaction in: {ready_time:.2f} seconds")
        
        # Kiểm tra xem tất cả tính năng đã được tải chưa
        if assistant.features_loaded.is_set():
            self.status_label.config(
                text="✅ Tất cả tính năng đã sẵn sàng",
                foreground="green"
            )
            
            # Tính tổng thời gian tải
            total_time = time.time() - self.start_time
            print(f"All features loaded in: {total_time:.2f} seconds")
            
            # Chỉ thông báo nếu chưa thông báo trước đó
            if not hasattr(assistant, 'basic_features_loaded') or not assistant.basic_features_loaded:
                self.input_entry.config(state=tk.NORMAL)
                self.send_button.config(state=tk.NORMAL)
                self.input_entry.focus_set()
                self._add_text("Trợ lý: Tôi đã sẵn sàng. Bạn cần giúp gì?")
        else:
            # Check again after 100ms
            self.root.after(100, self.monitor_feature_loading)

    # Phương thức _on_features_loaded đã được tích hợp vào monitor_feature_loading

    def process_input(self, event=None):
        user_input = self.input_entry.get().strip()
        if not user_input:
            return

        # Add user message immediately
        self._add_text(f"Bạn: {user_input}")
        self.input_entry.delete(0, tk.END)
        
        # Disable input while processing
        self.input_entry.config(state=tk.DISABLED)
        self.send_button.config(state=tk.DISABLED)
        self.processing = True
        
        # Show loading indicator
        self.status_label.config(
            text="⚡ Đang xử lý...", 
            foreground="orange"
        )
        self._add_text("Trợ lý: ⏳ Đang xử lý yêu cầu...")

        # Process command asynchronously
        # Tạo một wrapper cho callback để đảm bảo nó chạy trong luồng chính
        def main_thread_callback(result):
            # Đảm bảo callback được gọi trong luồng chính
            self.root.after(0, lambda: self._handle_response(result))
            
        assistant.run_feature_async(user_input.lower(), main_thread_callback)

    def _handle_response(self, response):
        """Handle the response from async processing."""
        print(f"DEBUG: _handle_response received: {response}")
        
        # Thực hiện cập nhật UI trực tiếp trong luồng chính
        try:
            # Remove loading message and add actual response
            self.output_area.config(state=tk.NORMAL)
            
            # Xóa thông báo "đang xử lý"
            lines = self.output_area.get("1.0", tk.END).split('\n')
            print(f"DEBUG: Last lines: {lines[-3:]}")
            for i in range(len(lines)):
                if "⏳ Đang xử lý yêu cầu..." in lines[i]:
                    line_num = i + 1  # Dòng bắt đầu từ 1
                    self.output_area.delete(f"{line_num}.0", f"{line_num+1}.0")
                    break
            
            # Add the actual response
            self.output_area.insert(tk.END, f"Trợ lý: {response}\n")
            print("DEBUG: UI updated with response")
            
            # Add AI suggestions if available
            try:
                from features.ai_enhancements import get_ai_predictions
                predictions = get_ai_predictions()
                if predictions:
                    self.output_area.insert(tk.END, "\n🤖 Gợi ý thông minh:\n")
                    for pred in predictions[:2]:
                        self.output_area.insert(tk.END, f"• {pred}\n")
            except Exception as e:
                print(f"DEBUG: Error getting AI predictions: {e}")
            
            self.output_area.config(state=tk.DISABLED)
            self.output_area.see(tk.END)
            
            # Re-enable input
            self.input_entry.config(state=tk.NORMAL)
            self.send_button.config(state=tk.NORMAL)
            self.processing = False
            
            # Update status
            self.status_label.config(
                text="✅ Sẵn sàng", 
                foreground="green"
            )
            
            # Cập nhật UI ngay lập tức
            self.root.update_idletasks()
        except Exception as e:
            print(f"DEBUG: Error in _handle_response: {e}")
            # Đảm bảo UI được cập nhật ngay cả khi có lỗi
            self.processing = False
            self.input_entry.config(state=tk.NORMAL)
            self.send_button.config(state=tk.NORMAL)
            self.status_label.config(text="✅ Sẵn sàng", foreground="green")
            # Cập nhật UI ngay lập tức ngay cả khi có lỗi
            self.root.update_idletasks()
            
            # Process any pending commands
            if self.pending_commands:
                next_command = self.pending_commands.pop(0)
                self.input_entry.insert(0, next_command)
                self.process_input()
                
            # Đảm bảo UI được cập nhật ngay lập tức
            self.root.update_idletasks()
            
        except Exception as e:
            print(f"DEBUG: Error in _handle_response: {e}")
            # Nếu có lỗi, vẫn cố gắng cập nhật UI
            self.root.update_idletasks()

    def _add_text(self, text):
        """Adds text to the output area and scrolls to the end."""
        self.output_area.config(state=tk.NORMAL)
        self.output_area.insert(tk.END, text + "\n")
        self.output_area.config(state=tk.DISABLED)
        self.output_area.see(tk.END)

def start_gui():
    print("Starting GUI initialization...")
    start_time = time.time()
    
    root = tk.Tk()
    app = AssistantGUI(root)
    
    # Log initial window creation time
    window_time = time.time() - start_time
    print(f"Window created in: {window_time:.2f} seconds")
    
    def on_window_appear(event=None):
        appear_time = time.time() - start_time
        print(f"Window fully rendered in: {appear_time:.2f} seconds")
        # Unbind after first trigger
        root.unbind('<Map>')
    
    # Bind to window map event to detect when window becomes visible
    root.bind('<Map>', on_window_appear)
    
    root.mainloop()
