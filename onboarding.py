import customtkinter as ctk
from tkinter import filedialog
import subprocess
import threading
import sys
import os
import winreg
import json

# --- UI Theme Configuration ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class OnboardingWizard(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("ConvertTLA Setup Wizard")
        self.geometry("650x500")
        self.resizable(False, False)

        # Base paths
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_path = os.path.join(self.script_dir, "config.json")

        try:
            self.iconbitmap(os.path.join(self.script_dir, "favicon.ico"))
        except:
            pass

        # Wizard App State Tracking
        self.current_step = 0
        self.steps = [
            self.show_welcome, 
            self.show_checks, 
            self.show_preferences, 
            self.show_integrations, 
            self.show_finish
        ]

        # User Configuration Variables
        self.hw_accel_var = ctk.BooleanVar(value=False)
        self.gpu_detected = False
        
        self.theme_var = ctk.StringVar(value="Dark")
        self.save_loc_var = ctk.StringVar(value="Source Folder")
        self.custom_path_var = ctk.StringVar(value="")
        
        self.shortcut_var = ctk.BooleanVar(value=True)
        self.context_menu_var = ctk.BooleanVar(value=True)

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
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    def next_step(self):
        if self.current_step < len(self.steps) - 1:
            self.current_step += 1
            self.clear_content()
            self.steps[self.current_step]()
            self.back_btn.configure(state="normal")
        else:
            self.save_configuration()
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
            "This setup wizard will verify your encoding engine, detect hardware\n"
            "acceleration capabilities, and personalize your workspace.\n\n"
            "Click 'Next' to initialize system validation."
        )
        ctk.CTkLabel(self.content_frame, text=description, font=ctk.CTkFont(size=13), justify="center").pack(pady=10)

    # --- STEP 2: Verification & Hardware Checks ---
    def show_checks(self):
        self.next_btn.configure(state="disabled")

        title = ctk.CTkLabel(self.content_frame, text="System & Hardware Verification", font=ctk.CTkFont(size=20, weight="bold"))
        title.pack(pady=(10, 20))

        self.py_status = ctk.CTkLabel(self.content_frame, text="⏳ Checking Python Runtime Environment...", anchor="w")
        self.py_status.pack(fill=ctk.X, padx=40, pady=8)

        self.ff_status = ctk.CTkLabel(self.content_frame, text="⏳ Checking FFmpeg Video Encoding Pipelines...", anchor="w")
        self.ff_status.pack(fill=ctk.X, padx=40, pady=8)

        self.gpu_status = ctk.CTkLabel(self.content_frame, text="⏳ Scanning for Dedicated GPUs...", anchor="w")
        self.gpu_status.pack(fill=ctk.X, padx=40, pady=8)

        # Container for the dynamic GPU opt-in toggle
        self.gpu_opt_in_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.gpu_opt_in_frame.pack(fill=ctk.X, padx=40, pady=10)

        threading.Thread(target=self.run_validation_logic, daemon=True).start()

    def run_validation_logic(self):
        py_valid = sys.version_info >= (3, 0)
        ff_valid = subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=0x08000000 if os.name == 'nt' else 0).returncode == 0
        
        # Hardware Scan using WMIC
        gpu_detected = False
        try:
            creationflags = 0x08000000 if os.name == 'nt' else 0
            wmic_output = subprocess.check_output(["wmic", "path", "win32_VideoController", "get", "name"], text=True, creationflags=creationflags)
            wmic_upper = wmic_output.upper()
            if "NVIDIA" in wmic_upper or "AMD" in wmic_upper or "RADEON" in wmic_upper:
                gpu_detected = True
        except Exception:
            pass

        self.after(0, lambda: self.update_check_ui(py_valid, ff_valid, gpu_detected))

    def update_check_ui(self, py, ff, gpu):
        if py: self.py_status.configure(text="✅ Python 3 Framework: Operational", text_color="#2ECC71")
        else: self.py_status.configure(text="❌ Python 3 Framework: Error", text_color="#E74C3C")

        if ff: self.ff_status.configure(text="✅ FFmpeg Core: Active", text_color="#2ECC71")
        else: self.ff_status.configure(text="❌ FFmpeg Core: Missing", text_color="#E74C3C")

        if gpu:
            self.gpu_detected = True
            self.hw_accel_var.set(True) # Default to on if found
            self.gpu_status.configure(text="🚀 Hardware Acceleration Detected (NVIDIA/AMD)!", text_color="#F1C40F", font=ctk.CTkFont(weight="bold"))
            
            # Show opt-in checkbox
            ctk.CTkLabel(self.gpu_opt_in_frame, text="Would you like to use your GPU for faster video conversions?").pack(anchor="w")
            ctk.CTkSwitch(self.gpu_opt_in_frame, text="Enable Hardware Acceleration (NVENC/AMF)", variable=self.hw_accel_var, progress_color="#2ECC71").pack(anchor="w", pady=5)
        else:
            self.gpu_status.configure(text="ℹ️ Standard Software Encoding Configured.", text_color="gray")

        if py and ff:
            self.next_btn.configure(state="normal")
        else:
            ctk.CTkLabel(self.content_frame, text="Please run installer.bat to correct missing dependencies.", text_color="#E74C3C", font=ctk.CTkFont(weight="bold")).pack(pady=20)

    # --- STEP 3: User Preferences ---
    def show_preferences(self):
        title = ctk.CTkLabel(self.content_frame, text="Personalize ConvertTLA", font=ctk.CTkFont(size=20, weight="bold"))
        title.pack(pady=(10, 20))

        # Theme Selection
        ctk.CTkLabel(self.content_frame, text="Default App Theme:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=20)
        
        def update_theme(choice):
            ctk.set_appearance_mode(choice)
            
        theme_menu = ctk.CTkOptionMenu(self.content_frame, values=["Dark", "Light", "System"], variable=self.theme_var, command=update_theme)
        theme_menu.pack(anchor="w", padx=20, pady=(5, 20))

        # Save Location
        ctk.CTkLabel(self.content_frame, text="Default Output Folder:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=20)
        
        def toggle_custom_path(choice):
            if choice == "Custom Folder...":
                folder = filedialog.askdirectory(title="Select Default Folder")
                if folder:
                    self.custom_path_var.set(folder)
                    self.save_loc_var.set("Custom Folder...")
                else:
                    self.save_loc_var.set("Source Folder") # Fallback if cancelled
            
        loc_menu = ctk.CTkOptionMenu(self.content_frame, values=["Source Folder", "Desktop", "Custom Folder..."], variable=self.save_loc_var, command=toggle_custom_path)
        loc_menu.pack(anchor="w", padx=20, pady=5)

        self.custom_path_label = ctk.CTkLabel(self.content_frame, textvariable=self.custom_path_var, text_color="gray", font=ctk.CTkFont(size=11))
        self.custom_path_label.pack(anchor="w", padx=20)

    # --- STEP 4: System Integrations ---
    def show_integrations(self):
        title = ctk.CTkLabel(self.content_frame, text="System Integrations", font=ctk.CTkFont(size=20, weight="bold"))
        title.pack(pady=(20, 10))

        ctk.CTkLabel(self.content_frame, text="How would you like to access ConvertTLA?", font=ctk.CTkFont(size=13)).pack(pady=10)

        # Shortcut Options
        ctk.CTkCheckBox(self.content_frame, text="Create Desktop Shortcut (.lnk)", variable=self.shortcut_var).pack(pady=15, padx=40, anchor="w")
        
        # Context Menu Option
        ctx_desc = "Add 'Convert with ConvertTLA' to Windows Right-Click Menu"
        ctk.CTkCheckBox(self.content_frame, text=ctx_desc, variable=self.context_menu_var).pack(pady=10, padx=40, anchor="w")
        ctk.CTkLabel(self.content_frame, text="  (Allows you to right-click media files and instantly open them in the app)", text_color="gray", font=ctk.CTkFont(size=11)).pack(anchor="w", padx=60)

    def build_system_integrations(self):
        if self.shortcut_var.get() and os.name == 'nt':
            try: self.generate_windows_shortcut()
            except Exception as e: print(f"Shortcut Error: {e}")
            
        if self.context_menu_var.get() and os.name == 'nt':
            try: self.generate_context_menu()
            except Exception as e: print(f"Context Menu Error: {e}")

    def generate_windows_shortcut(self):
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders") as key:
                desktop = os.path.expandvars(winreg.QueryValueEx(key, "Desktop")[0])
        except Exception:
            desktop = os.path.join(os.environ["USERPROFILE"], "Desktop")

        shortcut_path = os.path.join(desktop, "ConvertTLA.lnk")
        target_script = os.path.join(self.script_dir, "media_converter.py")
        icon_path = os.path.join(self.script_dir, "favicon.ico")

        # Command structure for silent PowerShell shortcut delivery
        ps_cmd = (
            f"$WshShell = New-Object -ComObject WScript.Shell; "
            f"$Shortcut = $WshShell.CreateShortcut('{shortcut_path}'); "
            f"$Shortcut.TargetPath = 'pythonw.exe'; "  
            f"$Shortcut.Arguments = '\"{target_script}\"'; "
            f"$Shortcut.WorkingDirectory = '{self.script_dir}'; "
        )
        if os.path.exists(icon_path):
            ps_cmd += f"$Shortcut.IconLocation = '{icon_path}'; "
            
        ps_cmd += "$Shortcut.Save()"
        subprocess.run(["powershell", "-Command", ps_cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=0x08000000)

    def generate_context_menu(self):
        """Injects a right-click context menu item directly into the Windows Registry for the current user."""
        target_script = os.path.join(self.script_dir, "media_converter.py")
        icon_path = os.path.join(self.script_dir, "favicon.ico")
        
        # Dynamically find the exact, absolute path to the Python interpreter running this script
        python_exe = sys.executable
        
        # Try to use pythonw.exe (hides the black console box), but fallback to python.exe if needed
        pythonw_exe = python_exe.replace("python.exe", "pythonw.exe")
        if not os.path.exists(pythonw_exe):
            pythonw_exe = python_exe

        # Build the exact, absolute command string so Windows never has to guess
        command_string = f'"{pythonw_exe}" "{target_script}" "%1"'

        try:
            # We use HKCU to avoid requiring Administrator privileges
            key_path = r"Software\Classes\*\shell\ConvertTLA"
            
            # Create root command key
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "Convert with ConvertTLA")
                if os.path.exists(icon_path):
                    winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, f'"{icon_path}"')
            
            # Create sub-command key mapped to the absolute Python path
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path + r"\command") as sub_key:
                winreg.SetValueEx(sub_key, "", 0, winreg.REG_SZ, command_string)
        except Exception as e:
            print(f"Failed to create context menu: {e}")

    # --- STEP 5: Finalization ---
    def save_configuration(self):
        """Saves all gathered preferences to a local config.json file."""
        config_data = {
            "theme": self.theme_var.get(),
            "save_location": self.save_loc_var.get(),
            "custom_path": self.custom_path_var.get(),
            "hardware_acceleration": self.hw_accel_var.get()
        }
        
        with open(self.config_path, "w") as config_file:
            json.dump(config_data, config_file, indent=4)
            
        # Run system integrations right before exiting
        self.build_system_integrations()

    def show_finish(self):
        title = ctk.CTkLabel(self.content_frame, text="Configuration Completed!", font=ctk.CTkFont(size=22, weight="bold"), text_color="#2ECC71")
        title.pack(pady=(40, 10))

        desc = (
            "ConvertTLA has been personalized and provisioned.\n\n"
            "Click 'Finish' to exit this setup routine and launch\n"
            "your configured conversion interface."
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