import customtkinter as ctk
import subprocess
import threading
import sys
import os

# --- UI Theme Configuration ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class OnboardingWizard(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("ConvertTLA Setup Wizard")
        self.geometry("600x450")
        self.resizable(False, False)

        # Get the absolute directory where onboarding.py lives
        self.script_dir = os.path.dirname(os.path.abspath(__file__))

        # Apply icon if available
        try:
            self.iconbitmap(os.path.join(self.script_dir, "favicon.ico"))
        except:
            pass

        # Wizard App State Tracking
        self.current_step = 0
        self.steps = [self.show_welcome, self.show_checks, self.show_shortcut, self.show_finish]

        # Component Containers
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.pack(fill=ctk.BOTH, expand=True, padx=30, pady=20)

        self.navigation_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.navigation_frame.pack(fill=ctk.X, side=ctk.BOTTOM, padx=30, pady=20)

        # Permanent Navigation Controls
        self.back_btn = ctk.CTkButton(self.navigation_frame, text="Back", command=self.previous_step, fg_color="#34495E", hover_color="#2C3E50", state="disabled")
        self.back_btn.pack(side=ctk.LEFT)

        self.next_btn = ctk.CTkButton(self.navigation_frame, text="Next", command=self.next_step)
        self.next_btn.pack(side=ctk.RIGHT)

        # Render first sequence
        self.steps[self.current_step]()

    def clear_content(self):
        """Clears old frames out of the viewport between steps."""
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    def next_step(self):
        if self.current_step < len(self.steps) - 1:
            self.current_step += 1
            self.clear_content()
            self.steps[self.current_step]()
            self.back_btn.configure(state="normal")
        else:
            # Complete and launch main engine
            self.launch_main_app()

    def previous_step(self):
        if self.current_step > 0:
            self.current_step -= 1
            self.clear_content()
            self.steps[self.current_step]()
            
            if self.current_step == 0:
                self.back_btn.configure(state="disabled")
            self.next_btn.configure(text="Next", state="normal")

    # --- STEP 1: Welcome Screen ---
    def show_welcome(self):
        title = ctk.CTkLabel(self.content_frame, text="Welcome to ConvertTLA", font=ctk.CTkFont(size=26, weight="bold"))
        title.pack(pady=(40, 10))

        tagline = ctk.CTkLabel(self.content_frame, text="The Ultimate Desktop Media & Image Converter", font=ctk.CTkFont(size=14, weight="bold"), text_color="#2E86C1")
        tagline.pack(pady=(0, 30))

        description = (
            "This setup wizard will instantly verify your core encoding engine settings,\n"
            "validate required environment configurations, and install desktop launch triggers.\n\n"
            "Click 'Next' to initialize system validation paths."
        )
        desc_label = ctk.CTkLabel(self.content_frame, text=description, font=ctk.CTkFont(size=13), justify="center")
        desc_label.pack(pady=10)

    # --- STEP 2: Verification Checks ---
    def show_checks(self):
        self.next_btn.configure(state="disabled")

        title = ctk.CTkLabel(self.content_frame, text="System Dependency Verification", font=ctk.CTkFont(size=20, weight="bold"))
        title.pack(pady=(10, 20))

        # Status Rows containers
        self.py_status = ctk.CTkLabel(self.content_frame, text="⏳ Checking Python Runtime Environment...", anchor="w")
        self.py_status.pack(fill=ctk.X, padx=40, pady=8)

        self.ff_status = ctk.CTkLabel(self.content_frame, text="⏳ Checking FFmpeg Video Encoding Pipelines...", anchor="w")
        self.ff_status.pack(fill=ctk.X, padx=40, pady=8)

        self.tk_status = ctk.CTkLabel(self.content_frame, text="⏳ Verifying Custom UI Component Libraries...", anchor="w")
        self.tk_status.pack(fill=ctk.X, padx=40, pady=8)

        # Trigger background calculation thread to keep UI interactive
        threading.Thread(target=self.run_validation_logic, daemon=True).start()

    def run_validation_logic(self):
        py_valid = sys.version_info >= (3, 0)
        ff_valid = subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=0x08000000 if os.name == 'nt' else 0).returncode == 0
        
        try:
            import customtkinter
            tk_valid = True
        except ImportError:
            tk_valid = False

        self.after(0, lambda: self.update_check_ui(py_valid, ff_valid, tk_valid))

    def update_check_ui(self, py, ff, tk_libs):
        if py: self.py_status.configure(text="✅ Python 3 Framework Runtime: Operational", text_color="#2ECC71")
        else: self.py_status.configure(text="❌ Python 3 Framework Runtime: Error", text_color="#E74C3C")

        if ff: self.ff_status.configure(text="✅ FFmpeg System Encoding Core: Active", text_color="#2ECC71")
        else: self.ff_status.configure(text="❌ FFmpeg System Encoding Core: Missing from PATH", text_color="#E74C3C")

        if tk_libs: self.tk_status.configure(text="✅ CustomTkinter Framework UI Libraries: Mounted", text_color="#2ECC71")
        else: self.tk_status.configure(text="❌ CustomTkinter Framework UI Libraries: Uninstalled", text_color="#E74C3C")

        if py and ff and tk_libs:
            self.next_btn.configure(state="normal")
        else:
            err_label = ctk.CTkLabel(self.content_frame, text="Please run installer.bat to automatically correct missing dependencies.", text_color="#E74C3C", font=ctk.CTkFont(weight="bold"))
            err_label.pack(pady=20)

    # --- STEP 3: Shortcut Configuration ---
    def show_shortcut(self):
        title = ctk.CTkLabel(self.content_frame, text="Create Desktop Launch Trigger", font=ctk.CTkFont(size=20, weight="bold"))
        title.pack(pady=(20, 10))

        info_text = "Would you like to deploy a desktop icon path to quickly launch ConvertTLA anytime?"
        ctk.CTkLabel(self.content_frame, text=info_text, font=ctk.CTkFont(size=13)).pack(pady=10)

        self.shortcut_var = ctk.BooleanVar(value=True)
        cb = ctk.CTkCheckBox(self.content_frame, text="Create Desktop Shortcut Link (.lnk)", variable=self.shortcut_var)
        cb.pack(pady=20)

    def generate_windows_shortcut(self):
        """Builds a precise WScript shell map inside a tiny PowerShell execution to cleanly create a .lnk shortcut."""
        desktop = os.path.join(os.environ["USERPROFILE"], "Desktop")
        shortcut_path = os.path.join(desktop, "ConvertTLA.lnk")
        
        # Explicitly use absolute targets based on script directory
        target_script = os.path.join(self.script_dir, "media_converter.py")
        icon_path = os.path.join(self.script_dir, "favicon.ico")

        # Command structure for silent PowerShell shortcut delivery
        ps_cmd = (
            f"$WshShell = New-Object -ComObject WScript.Shell; "
            f"$Shortcut = $WshShell.CreateShortcut('{shortcut_path}'); "
            f"$Shortcut.TargetPath = 'pythonw.exe'; "  # pythonw hides the black console box popup
            f"$Shortcut.Arguments = '\"{target_script}\"'; "
            f"$Shortcut.WorkingDirectory = '{self.script_dir}'; "
        )
        
        if os.path.exists(icon_path):
            ps_cmd += f"$Shortcut.IconLocation = '{icon_path}'; "
            
        ps_cmd += "$Shortcut.Save()"

        subprocess.run(["powershell", "-Command", ps_cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=0x08000000)

    # --- STEP 4: Success / Finish Screen ---
    def show_finish(self):
        if self.shortcut_var.get() and os.name == 'nt':
            try:
                self.generate_windows_shortcut()
            except:
                pass

        title = ctk.CTkLabel(self.content_frame, text="Configuration Completed!", font=ctk.CTkFont(size=22, weight="bold"), text_color="#2ECC71")
        title.pack(pady=(40, 10))

        desc = (
            "ConvertTLA has been provisioned and is ready for heavy load.\n\n"
            "Click 'Finish' to exit this setup routine and automatically launch\n"
            "your brand new conversion interface."
        )
        ctk.CTkLabel(self.content_frame, text=desc, font=ctk.CTkFont(size=13), justify="center").pack(pady=20)
        
        self.next_btn.configure(text="Finish")

    def launch_main_app(self):
        self.destroy()
        target_app = os.path.join(self.script_dir, "media_converter.py")
        if os.path.exists(target_app):
            subprocess.Popen([sys.executable, target_app])


if __name__ == "__main__":
    app = OnboardingWizard()
    app.mainloop()