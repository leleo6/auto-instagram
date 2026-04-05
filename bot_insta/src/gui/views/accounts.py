import customtkinter as ctk
import threading
from bot_insta.src.gui.style import FONT_SMALL, FONT_MAIN, ACCENT_TEAL
from bot_insta.src.core.account_manager import acc_manager
from bot_insta.src.gui.utils import create_platform_icon
from bot_insta.src.gui.bootstrap import PROJECT_ROOT

class AccountsView(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        
        ctk.CTkLabel(header, text="Linked Accounts", font=FONT_MAIN, text_color="#c0c0c0").pack(side="left", padx=10)
        
        btn_add = ctk.CTkButton(header, text="+ Add Account", font=FONT_SMALL, width=120,
                                fg_color=ACCENT_TEAL, hover_color="#006060",
                                command=self.open_add_modal)
        btn_add.pack(side="right", padx=10)

        self.list_wrap = ctk.CTkScrollableFrame(self, fg_color="#1c1f27", corner_radius=8)
        self.list_wrap.grid(row=1, column=0, sticky="nsew")
        self.list_wrap.grid_columnconfigure(0, weight=1)

        self.refresh_list()

    def refresh_list(self):
        for widget in self.list_wrap.winfo_children():
            widget.destroy()

        accounts = acc_manager.list_accounts()
        if not accounts:
            ctk.CTkLabel(self.list_wrap, text="No accounts linked. Add one to publish.",
                         font=FONT_SMALL, text_color="#555").pack(pady=40)
            return

        for acc in accounts:
            card = ctk.CTkFrame(self.list_wrap, fg_color="#23262e", corner_radius=6)
            card.pack(fill="x", padx=10, pady=5)
            
            alias = acc.get('name', 'Account')
            icon_img = create_platform_icon(acc['platform'])
            info = f"  {alias}"

            ctk.CTkLabel(card, text=info, image=icon_img, compound="left", padx=8, font=FONT_MAIN, text_color="white").pack(side="left", padx=15, pady=15)
            
            # Status badge
            status = acc.get("status", "Unknown")
            status_color = "#888"
            if status == "Active": status_color = "#4dcf9a"
            elif status == "Error": status_color = "#e05555"

            lbl_status = ctk.CTkLabel(card, text=f"• {status}", font=FONT_SMALL, text_color=status_color)
            lbl_status.pack(side="left", padx=15)

            # Actions
            btn_del = ctk.CTkButton(card, text="Delete", font=FONT_SMALL, width=60, fg_color="#e05555", hover_color="#803030", command=lambda a=acc['id']: self.delete_acc(a))
            btn_del.pack(side="right", padx=10)

            btn_verify = ctk.CTkButton(card, text="Verify", font=FONT_SMALL, width=60, fg_color="#2e323c", hover_color="#444", command=lambda a=acc['id']: self.verify_acc(a))
            btn_verify.pack(side="right", padx=10)

    def verify_acc(self, acc_id):
        acc = acc_manager.get_account(acc_id)
        if not acc: return
        
        acc_manager.update_status(acc_id, "Verifying...")
        self.refresh_list()
        
        def run_verification():
            try:
                creds = acc.get("credentials", {})
                platform = acc.get("platform")
                if platform == "Instagram":
                    from instagrapi import Client
                    cl = Client()
                    # Real login attempt, throws exception if unauthorized
                    session_path = PROJECT_ROOT / "bot_insta" / "config" / f"session_{acc_id}.json"
                    if session_path.exists():
                        try: cl.load_settings(session_path)
                        except: pass
                    cl.login(creds.get("username", ""), creds.get("password", ""))
                    cl.dump_settings(session_path)
                    acc_manager.update_status(acc_id, "Active")
                elif platform == "YouTube":
                    import json, os
                    path = creds.get("youtube_client_secrets", "")
                    if os.path.exists(path) and path.endswith('.json'):
                        with open(path, 'r') as f:
                            json.load(f)
                        acc_manager.update_status(acc_id, "Active")
                    else:
                        raise ValueError("Invalid client_secrets path")
                elif platform == "TikTok":
                    path = creds.get("tiktok_session_id", "")
                    if len(path) > 7:
                        acc_manager.update_status(acc_id, "Active")
                    else:
                        raise ValueError("Invalid Session ID / cookie path")
            except Exception as e:
                import logging
                logging.error(f"Verify Error for {acc_id}: {e}")
                acc_manager.update_status(acc_id, "Error")
            finally:
                self.after(0, self.refresh_list)
                
        threading.Thread(target=run_verification, daemon=True).start()

    def delete_acc(self, acc_id):
        acc_manager.delete_account(acc_id)
        self.app.dashboard.refresh_profiles()
        self.refresh_list()

    def open_add_modal(self):
        AddAccountModal(self)

class AddAccountModal(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Add Account")
        self.geometry("400x380")
        self.resizable(False, False)
        self.configure(fg_color="#1c1f27")
        self.transient(parent.app)
        self.after(150, self.grab_set)

        self.parent_view = parent

        ctk.CTkLabel(self, text="Account Name (Alias):", font=FONT_SMALL, text_color="#c0c0c0").pack(pady=(20, 5))
        self.name_entry = ctk.CTkEntry(self, width=250, fg_color="#23262e", border_color="#333", text_color="white")
        self.name_entry.pack(pady=5)

        self.platform_var = ctk.StringVar(value="Instagram")
        ctk.CTkLabel(self, text="Platform:", font=FONT_MAIN, text_color="#c0c0c0").pack(pady=(15, 5))
        
        self.opt_platform = ctk.CTkOptionMenu(self, values=["Instagram", "TikTok", "YouTube"], 
                                              variable=self.platform_var, command=self.on_platform_change)
        self.opt_platform.pack(pady=5)

        self.form_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.form_frame.pack(fill="both", expand=True, padx=20, pady=10)

        self.entries = {}
        self.on_platform_change("Instagram")

        ctk.CTkButton(self, text="Save", font=FONT_MAIN, fg_color=ACCENT_TEAL, hover_color="#006060", command=self.save).pack(pady=20)

    def on_platform_change(self, choice):
        for widget in self.form_frame.winfo_children():
            widget.destroy()
        self.entries.clear()

        if choice == "Instagram":
            ctk.CTkLabel(self.form_frame, text="Username:", font=FONT_SMALL, text_color="#888").pack(anchor="w")
            e1 = ctk.CTkEntry(self.form_frame, width=250, fg_color="#23262e", border_color="#333", text_color="white")
            e1.pack(pady=5)
            ctk.CTkLabel(self.form_frame, text="Password:", font=FONT_SMALL, text_color="#888").pack(anchor="w")
            e2 = ctk.CTkEntry(self.form_frame, width=250, show="*", fg_color="#23262e", border_color="#333", text_color="white")
            e2.pack(pady=5)
            self.entries = {"username": e1, "password": e2}
        elif choice == "TikTok":
            ctk.CTkLabel(self.form_frame, text="Session ID string / cookie.txt path:", font=FONT_SMALL, text_color="#888").pack(anchor="w")
            e1 = ctk.CTkEntry(self.form_frame, width=250, fg_color="#23262e", border_color="#333", text_color="white")
            e1.pack(pady=5)
            self.entries = {"tiktok_session_id": e1}
        elif choice == "YouTube":
            ctk.CTkLabel(self.form_frame, text="Path to client_secrets.json:", font=FONT_SMALL, text_color="#888").pack(anchor="w")
            e1 = ctk.CTkEntry(self.form_frame, width=250, fg_color="#23262e", border_color="#333", text_color="white")
            e1.pack(pady=5)
            self.entries = {"youtube_client_secrets": e1}

    def save(self):
        alias_name = self.name_entry.get().strip() or "My Account"
        platform = self.platform_var.get()
        creds = {k: v.get() for k, v in self.entries.items()}
        acc_manager.add_account(alias_name, platform, creds)
        self.parent_view.refresh_list()
        self.parent_view.app.dashboard.refresh_profiles()
        self.destroy()
