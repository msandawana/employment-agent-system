import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk
import os
import subprocess
import platform
from datetime import datetime

from database import *
from auth import *

# Initialize database
create_candidates_table()
create_users_table()
create_default_users()
create_settings_table()


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Employment Agent System")
        self.root.geometry("1400x800")
        self.root.minsize(1000, 600)
        self.current_role = None
        self.current_username = None
        self.login_screen()

    # ---------------- UTIL ----------------
    def clear_screen(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def center_window(self, window, width, height):
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        window.geometry(f"{width}x{height}+{x}+{y}")

    def open_file(self, filepath):
        if not filepath or not os.path.exists(filepath):
            messagebox.showerror("Error", "File not found")
            return
        try:
            if platform.system() == 'Windows':
                os.startfile(filepath)
            elif platform.system() == 'Darwin':
                subprocess.call(['open', filepath])
            else:
                subprocess.call(['xdg-open', filepath])
        except Exception as e:
            messagebox.showerror("Error", f"Could not open file: {str(e)}")

    # ---------------- LOGIN ----------------
    def login_screen(self):
        self.clear_screen()
        main_frame = ttk.Frame(self.root)
        main_frame.pack(expand=True, fill="both")

        login_frame = ttk.Frame(main_frame, padding=40)
        login_frame.place(relx=0.5, rely=0.5, anchor="center")

        ttk.Label(login_frame, text="Employment Agent System",
                  font=("Arial", 24, "bold")).grid(row=0, column=0, columnspan=2, pady=(0, 30))

        ttk.Label(login_frame, text="Username:", font=("Arial", 12)).grid(
            row=1, column=0, sticky="e", padx=(0, 10), pady=10)
        self.username_entry = ttk.Entry(login_frame, width=30, font=("Arial", 11))
        self.username_entry.grid(row=1, column=1, pady=10)
        self.username_entry.focus()

        ttk.Label(login_frame, text="Password:", font=("Arial", 12)).grid(
            row=2, column=0, sticky="e", padx=(0, 10), pady=10)
        self.password_entry = ttk.Entry(login_frame, show="●", width=30, font=("Arial", 11))
        self.password_entry.grid(row=2, column=1, pady=10)

        self.username_entry.bind("<Return>", lambda e: self.password_entry.focus())
        self.password_entry.bind("<Return>", lambda e: self.login())

        ttk.Button(login_frame, text="Login", command=self.login,
                   width=20).grid(row=3, column=0, columnspan=2, pady=20)

        ttk.Label(login_frame,
                  text="Default credentials:\nUsername: admin | Password: Admin@2024!",
                  font=("Arial", 9), foreground="gray").grid(row=4, column=0, columnspan=2, pady=(10, 0))

    def login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        if not username or not password:
            messagebox.showerror("Error", "Please enter both username and password")
            return
        role, message = authenticate(username, password)
        if role:
            self.current_role = role
            self.current_username = username
            self.main_app()
        else:
            messagebox.showerror("Login Failed", message)
            self.password_entry.delete(0, tk.END)

    def logout(self):
        if messagebox.askyesno("Logout", "Are you sure you want to logout?"):
            self.current_role = None
            self.current_username = None
            self.login_screen()

    # ---------------- MAIN APP ----------------
    def main_app(self):
        self.clear_screen()

        header_frame = ttk.Frame(self.root)
        header_frame.pack(fill="x", side="top")

        try:
            logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo.png")
            if os.path.exists(logo_path):
                image = Image.open(logo_path)
                image = image.resize((160, 80), Image.Resampling.LANCZOS)
                self.logo_img = ImageTk.PhotoImage(image)
                ttk.Label(header_frame, image=self.logo_img).pack(side="left", padx=10, pady=5)
        except Exception as e:
            print(f"Error loading logo: {e}")

        user_info_frame = ttk.Frame(header_frame)
        user_info_frame.pack(side="right", padx=20, pady=10)
        ttk.Label(user_info_frame,
                  text=f"Logged in as: {self.current_username} ({self.current_role.title()})",
                  font=("Arial", 10, "bold")).pack()

        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=5, pady=5)

        self.candidate_tab = ttk.Frame(notebook)
        notebook.add(self.candidate_tab, text="📋 Candidates")
        self.build_candidates()

        if self.current_role == "admin":
            self.users_tab = ttk.Frame(notebook)
            notebook.add(self.users_tab, text="👥 User Management")
            self.build_users()

        settings_tab = ttk.Frame(notebook)
        notebook.add(settings_tab, text="⚙️ Settings")
        self.build_settings(settings_tab)

    # ---------------- CANDIDATES TAB ----------------
    def build_candidates(self):
        toolbar = ttk.Frame(self.candidate_tab)
        toolbar.pack(fill="x", padx=10, pady=10)

        search_frame = ttk.LabelFrame(toolbar, text="Search", padding=5)
        search_frame.pack(side="left", padx=(0, 10))
        ttk.Label(search_frame, text="🔍").pack(side="left", padx=(0, 5))
        self.search_entry = ttk.Entry(search_frame, width=30)
        self.search_entry.pack(side="left", padx=5)
        self.search_entry.bind("<KeyRelease>", self.live_search)
        ttk.Button(search_frame, text="Clear",
                   command=lambda: (self.search_entry.delete(0, tk.END), self.load_candidates()),
                   width=8).pack(side="left", padx=5)

        action_frame = ttk.Frame(toolbar)
        action_frame.pack(side="left", padx=10)
        ttk.Button(action_frame, text="➕ Add Candidate", command=self.add_candidate_window).pack(side="left", padx=2)
        ttk.Button(action_frame, text="✏️ Edit", command=lambda: self.edit_candidate(None)).pack(side="left", padx=2)
        ttk.Button(action_frame, text="🗑️ Delete", command=self.delete_candidate).pack(side="left", padx=2)

        export_frame = ttk.Frame(toolbar)
        export_frame.pack(side="right")
        ttk.Button(export_frame, text="📊 Export Excel", command=self.export_excel).pack(side="left", padx=2)
        ttk.Button(export_frame, text="📄 Export PDF", command=self.export_pdf).pack(side="left", padx=2)

        tree_frame = ttk.Frame(self.candidate_tab)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        vsb.pack(side="right", fill="y")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")
        hsb.pack(side="bottom", fill="x")

        columns = ("ID", "Full Name", "ID Number", "Cell", "Email", "Experience", "CV")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings",
                                  yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.config(command=self.tree.yview)
        hsb.config(command=self.tree.xview)

        column_widths = {"ID": 50, "Full Name": 200, "ID Number": 130,
                         "Cell": 130, "Email": 200, "Experience": 200, "CV": 100}
        for col in columns:
            self.tree.heading(col, text=col, command=lambda c=col: self.sort_treeview(c))
            self.tree.column(col, width=column_widths.get(col, 150), anchor="w")

        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", self.edit_candidate)
        self.tree.bind("<Button-3>", self.show_context_menu)

        self.status_bar = ttk.Label(self.candidate_tab, text="Ready", relief=tk.SUNKEN, anchor="w")
        self.status_bar.pack(fill="x", side="bottom")

        self.load_candidates()

    def load_candidates(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        rows = get_all_candidates()
        for row in rows:
            cv_display = "✓ Has CV" if row[6] else "✗ No CV"
            self.tree.insert("", "end", values=list(row[:6]) + [cv_display], tags=(row[6],))
        self.status_bar.config(text=f"Total candidates: {len(rows)}")

    def live_search(self, event):
        term = self.search_entry.get().strip()
        for item in self.tree.get_children():
            self.tree.delete(item)
        rows = search_candidates(term) if term else get_all_candidates()
        for row in rows:
            cv_display = "✓ Has CV" if row[6] else "✗ No CV"
            self.tree.insert("", "end", values=list(row[:6]) + [cv_display], tags=(row[6],))
        self.status_bar.config(text=f"Found {len(rows)} candidate(s)")

    def sort_treeview(self, col):
        items = [(self.tree.set(item, col), item) for item in self.tree.get_children('')]
        items.sort()
        for index, (val, item) in enumerate(items):
            self.tree.move(item, '', index)

    def show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            menu = tk.Menu(self.root, tearoff=0)
            menu.add_command(label="✏️ Edit", command=lambda: self.edit_candidate(None))
            menu.add_command(label="📄 Open CV", command=self.open_cv)
            menu.add_separator()
            menu.add_command(label="🗑️ Delete", command=self.delete_candidate)
            menu.post(event.x_root, event.y_root)

    def open_cv(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a candidate first")
            return
        cv_path = self.tree.item(selected)["tags"][0]
        if cv_path:
            self.open_file(cv_path)
        else:
            messagebox.showinfo("Info", "No CV file available for this candidate")

    def delete_candidate(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a candidate to delete")
            return
        values = self.tree.item(selected)["values"]
        if messagebox.askyesno("Confirm Delete",
                                f"Delete {values[1]}?\n\nThis action cannot be undone."):
            success, message = delete_candidate(values[0])
            if success:
                messagebox.showinfo("Success", message)
                self.load_candidates()
            else:
                messagebox.showerror("Error", message)

    def add_candidate_window(self):
        win = tk.Toplevel(self.root)
        win.title("Add New Candidate")
        win.transient(self.root)
        win.grab_set()
        self.center_window(win, 500, 560)

        form_frame = ttk.Frame(win, padding=20)
        form_frame.pack(fill="both", expand=True)
        ttk.Label(form_frame, text="Add New Candidate", font=("Arial", 16, "bold")).grid(
            row=0, column=0, columnspan=2, pady=(0, 20))

        fields = [("Full Name *", "full_name"), ("ID Number", "id_number"),
                  ("Cell Phone", "cell"), ("Email", "email"), ("Experience", "experience")]
        entries = {}
        for i, (label_text, field_name) in enumerate(fields, 1):
            ttk.Label(form_frame, text=label_text, font=("Arial", 10)).grid(
                row=i, column=0, sticky="w", pady=8, padx=(0, 10))
            if field_name == "experience":
                w = tk.Text(form_frame, width=35, height=4, font=("Arial", 10))
                w.grid(row=i, column=1, pady=8, sticky="ew")
            else:
                w = ttk.Entry(form_frame, width=35, font=("Arial", 10))
                w.grid(row=i, column=1, pady=8, sticky="ew")
            entries[field_name] = w

        row_num = len(fields) + 1
        ttk.Label(form_frame, text="CV File", font=("Arial", 10)).grid(
            row=row_num, column=0, sticky="w", pady=8, padx=(0, 10))
        cv_frame = ttk.Frame(form_frame)
        cv_frame.grid(row=row_num, column=1, pady=8, sticky="ew")
        cv_path = tk.StringVar()
        ttk.Label(cv_frame, textvariable=cv_path, foreground="gray", wraplength=250).pack(side="top", anchor="w")

        def browse_cv():
            f = filedialog.askopenfilename(title="Select CV",
                filetypes=[("PDF", "*.pdf"), ("Word", "*.doc *.docx"), ("All", "*.*")])
            if f:
                cv_path.set(f)

        ttk.Button(cv_frame, text="Browse...", command=browse_cv, width=15).pack(side="top", anchor="w", pady=(5, 0))

        row_num += 1
        btn_frame = ttk.Frame(form_frame)
        btn_frame.grid(row=row_num, column=0, columnspan=2, pady=20)

        def save_candidate():
            full_name = entries["full_name"].get().strip()
            if not full_name:
                messagebox.showerror("Error", "Full name is required")
                return
            success, message, _ = add_candidate(
                full_name,
                entries["id_number"].get().strip(),
                entries["cell"].get().strip(),
                entries["email"].get().strip(),
                entries["experience"].get("1.0", tk.END).strip(),
                cv_path.get()
            )
            if success:
                messagebox.showinfo("Success", message)
                win.destroy()
                self.load_candidates()
            else:
                messagebox.showerror("Error", message)

        ttk.Button(btn_frame, text="💾 Save", command=save_candidate, width=15).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="✖ Cancel", command=win.destroy, width=15).pack(side="left", padx=5)
        entries["full_name"].focus()

    def edit_candidate(self, event):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a candidate to edit")
            return
        values = self.tree.item(selected)["values"]
        cv_path_current = self.tree.item(selected)["tags"][0]
        candidate_id = values[0]

        win = tk.Toplevel(self.root)
        win.title("Edit Candidate")
        win.transient(self.root)
        win.grab_set()
        self.center_window(win, 500, 560)

        form_frame = ttk.Frame(win, padding=20)
        form_frame.pack(fill="both", expand=True)
        ttk.Label(form_frame, text="Edit Candidate", font=("Arial", 16, "bold")).grid(
            row=0, column=0, columnspan=2, pady=(0, 20))

        fields = [("Full Name *", "full_name", values[1]), ("ID Number", "id_number", values[2]),
                  ("Cell Phone", "cell", values[3]), ("Email", "email", values[4]),
                  ("Experience", "experience", values[5])]
        entries = {}
        for i, (label_text, field_name, value) in enumerate(fields, 1):
            ttk.Label(form_frame, text=label_text, font=("Arial", 10)).grid(
                row=i, column=0, sticky="w", pady=8, padx=(0, 10))
            if field_name == "experience":
                w = tk.Text(form_frame, width=35, height=4, font=("Arial", 10))
                w.insert("1.0", value if value else "")
                w.grid(row=i, column=1, pady=8, sticky="ew")
            else:
                w = ttk.Entry(form_frame, width=35, font=("Arial", 10))
                w.insert(0, value if value else "")
                w.grid(row=i, column=1, pady=8, sticky="ew")
            entries[field_name] = w

        row_num = len(fields) + 1
        ttk.Label(form_frame, text="CV File", font=("Arial", 10)).grid(
            row=row_num, column=0, sticky="w", pady=8, padx=(0, 10))
        cv_frame = ttk.Frame(form_frame)
        cv_frame.grid(row=row_num, column=1, pady=8, sticky="ew")
        cv_path = tk.StringVar(value=cv_path_current if cv_path_current else "No CV uploaded")
        ttk.Label(cv_frame, textvariable=cv_path, foreground="gray", wraplength=250).pack(side="top", anchor="w")

        btn_cv = ttk.Frame(cv_frame)
        btn_cv.pack(side="top", anchor="w", pady=(5, 0))

        def browse_cv():
            f = filedialog.askopenfilename(title="Select CV",
                filetypes=[("PDF", "*.pdf"), ("Word", "*.doc *.docx"), ("All", "*.*")])
            if f:
                cv_path.set(f)

        ttk.Button(btn_cv, text="Change CV", command=browse_cv, width=12).pack(side="left", padx=(0, 5))
        if cv_path_current:
            ttk.Button(btn_cv, text="Open CV",
                       command=lambda: self.open_file(cv_path_current), width=12).pack(side="left")

        row_num += 1
        btn_frame = ttk.Frame(form_frame)
        btn_frame.grid(row=row_num, column=0, columnspan=2, pady=20)

        def update_candidate_data():
            full_name = entries["full_name"].get().strip()
            if not full_name:
                messagebox.showerror("Error", "Full name is required")
                return
            cv_file = cv_path.get() if cv_path.get() != "No CV uploaded" else cv_path_current
            success, message = update_candidate(
                candidate_id, full_name,
                entries["id_number"].get().strip(),
                entries["cell"].get().strip(),
                entries["email"].get().strip(),
                entries["experience"].get("1.0", tk.END).strip(),
                cv_file
            )
            if success:
                messagebox.showinfo("Success", message)
                win.destroy()
                self.load_candidates()
            else:
                messagebox.showerror("Error", message)

        ttk.Button(btn_frame, text="💾 Update", command=update_candidate_data, width=15).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="✖ Cancel", command=win.destroy, width=15).pack(side="left", padx=5)

    def export_excel(self):
        rows = get_all_candidates()
        if not rows:
            messagebox.showinfo("Info", "No candidates to export")
            return
        filename = filedialog.asksaveasfilename(
            defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")],
            initialfile=f"candidates_{datetime.now().strftime('%Y%m%d')}.xlsx")
        if filename:
            success, message = export_candidates_to_excel(rows, filename)
            if success:
                messagebox.showinfo("Success", message)
                if messagebox.askyesno("Open?", "Open the exported file?"):
                    self.open_file(filename)
            else:
                messagebox.showerror("Error", message)

    def export_pdf(self):
        rows = get_all_candidates()
        if not rows:
            messagebox.showinfo("Info", "No candidates to export")
            return
        filename = filedialog.asksaveasfilename(
            defaultextension=".pdf", filetypes=[("PDF", "*.pdf")],
            initialfile=f"candidates_{datetime.now().strftime('%Y%m%d')}.pdf")
        if filename:
            success, message = export_candidates_to_pdf(rows, filename)
            if success:
                messagebox.showinfo("Success", message)
                if messagebox.askyesno("Open?", "Open the exported file?"):
                    self.open_file(filename)
            else:
                messagebox.showerror("Error", message)

    # ---------------- USER MANAGEMENT TAB ----------------
    def build_users(self):
        toolbar = ttk.Frame(self.users_tab)
        toolbar.pack(fill="x", padx=10, pady=10)
        ttk.Button(toolbar, text="➕ Create User", command=self.create_user_window).pack(side="left", padx=5)
        ttk.Button(toolbar, text="🔓 Unlock User", command=self.unlock_user).pack(side="left", padx=5)
        ttk.Button(toolbar, text="🗑️ Delete User", command=self.delete_user).pack(side="left", padx=5)

        tree_frame = ttk.Frame(self.users_tab)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        vsb.pack(side="right", fill="y")
        columns = ("ID", "Username", "Role", "Active", "Created", "Last Login")
        self.user_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", yscrollcommand=vsb.set)
        vsb.config(command=self.user_tree.yview)
        for col in columns:
            self.user_tree.heading(col, text=col)
            self.user_tree.column(col, width=150)
        self.user_tree.pack(fill="both", expand=True)

        ttk.Button(self.users_tab, text="🔄 Activate/Deactivate User",
                   command=self.toggle_user_status).pack(pady=10)
        self.load_users()

    def load_users(self):
        for item in self.user_tree.get_children():
            self.user_tree.delete(item)
        for row in get_all_users():
            self.user_tree.insert("", "end", values=(
                row[0], row[1], row[2].title(),
                "✓ Active" if row[3] == 1 else "✗ Inactive",
                row[4][:10] if row[4] else "N/A",
                row[5][:16] if row[5] else "Never"
            ))

    def create_user_window(self):
        win = tk.Toplevel(self.root)
        win.title("Create New User")
        win.transient(self.root)
        win.grab_set()
        self.center_window(win, 450, 400)

        form_frame = ttk.Frame(win, padding=20)
        form_frame.pack(fill="both", expand=True)
        ttk.Label(form_frame, text="Create New User", font=("Arial", 16, "bold")).grid(
            row=0, column=0, columnspan=2, pady=(0, 20))

        ttk.Label(form_frame, text="Username *").grid(row=1, column=0, sticky="w", pady=8)
        username_entry = ttk.Entry(form_frame, width=30)
        username_entry.grid(row=1, column=1, pady=8)
        username_entry.focus()

        ttk.Label(form_frame, text="Password *").grid(row=2, column=0, sticky="w", pady=8)
        password_entry = ttk.Entry(form_frame, show="●", width=30)
        password_entry.grid(row=2, column=1, pady=8)

        ttk.Label(form_frame, text="Confirm Password *").grid(row=3, column=0, sticky="w", pady=8)
        confirm_entry = ttk.Entry(form_frame, show="●", width=30)
        confirm_entry.grid(row=3, column=1, pady=8)

        ttk.Label(form_frame, text="Role *").grid(row=4, column=0, sticky="w", pady=8)
        role_var = tk.StringVar(value="user")
        role_frame = ttk.Frame(form_frame)
        role_frame.grid(row=4, column=1, sticky="w", pady=8)
        ttk.Radiobutton(role_frame, text="User", variable=role_var, value="user").pack(side="left", padx=(0, 10))
        ttk.Radiobutton(role_frame, text="Admin", variable=role_var, value="admin").pack(side="left")

        ttk.Label(form_frame,
                  text="Password: 8+ chars, uppercase, lowercase, number",
                  font=("Arial", 8), foreground="gray").grid(row=5, column=0, columnspan=2, pady=5, sticky="w")

        def save_user():
            if password_entry.get() != confirm_entry.get():
                messagebox.showerror("Error", "Passwords do not match")
                return
            success, message = create_user(username_entry.get().strip(), password_entry.get(), role_var.get())
            if success:
                messagebox.showinfo("Success", message)
                win.destroy()
                self.load_users()
            else:
                messagebox.showerror("Error", message)

        btn_frame = ttk.Frame(form_frame)
        btn_frame.grid(row=6, column=0, columnspan=2, pady=20)
        ttk.Button(btn_frame, text="💾 Create", command=save_user, width=15).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="✖ Cancel", command=win.destroy, width=15).pack(side="left", padx=5)

    def toggle_user_status(self):
        selected = self.user_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a user")
            return
        values = self.user_tree.item(selected)["values"]
        new_active = 0 if "Active" in values[3] else 1
        action = "activate" if new_active else "deactivate"
        if messagebox.askyesno("Confirm", f"{action.title()} user '{values[1]}'?"):
            success, message = set_user_active(values[0], new_active)
            if success:
                self.load_users()
            else:
                messagebox.showerror("Error", message)

    def unlock_user(self):
        selected = self.user_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a user")
            return
        values = self.user_tree.item(selected)["values"]
        if messagebox.askyesno("Confirm", f"Unlock account for '{values[1]}'?"):
            success, message = unlock_user(values[0])
            messagebox.showinfo("Success" if success else "Error", message)

    def delete_user(self):
        selected = self.user_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a user")
            return
        values = self.user_tree.item(selected)["values"]
        if messagebox.askyesno("Confirm Delete", f"Delete user '{values[1]}'?\n\nThis cannot be undone."):
            success, message = delete_user(values[0])
            if success:
                messagebox.showinfo("Success", message)
                self.load_users()
            else:
                messagebox.showerror("Error", message)

    # ---------------- SETTINGS TAB ----------------
    def build_settings(self, parent):
        settings_frame = ttk.Frame(parent, padding=20)
        settings_frame.pack(fill="both", expand=True)

        ttk.Label(settings_frame, text="Settings & Profile",
                  font=("Arial", 18, "bold")).pack(pady=(0, 30))

        pw_frame = ttk.LabelFrame(settings_frame, text="Change Password", padding=20)
        pw_frame.pack(fill="x", pady=10)

        ttk.Label(pw_frame, text="Current Password:").grid(row=0, column=0, sticky="w", pady=5)
        current_pw = ttk.Entry(pw_frame, show="●", width=30)
        current_pw.grid(row=0, column=1, pady=5, padx=10)

        ttk.Label(pw_frame, text="New Password:").grid(row=1, column=0, sticky="w", pady=5)
        new_pw = ttk.Entry(pw_frame, show="●", width=30)
        new_pw.grid(row=1, column=1, pady=5, padx=10)

        ttk.Label(pw_frame, text="Confirm New Password:").grid(row=2, column=0, sticky="w", pady=5)
        confirm_pw = ttk.Entry(pw_frame, show="●", width=30)
        confirm_pw.grid(row=2, column=1, pady=5, padx=10)

        def change_pw():
            if not current_pw.get() or not new_pw.get():
                messagebox.showerror("Error", "All fields are required")
                return
            if new_pw.get() != confirm_pw.get():
                messagebox.showerror("Error", "New passwords do not match")
                return
            role, _ = authenticate(self.current_username, current_pw.get())
            if not role:
                messagebox.showerror("Error", "Current password is incorrect")
                return
            success, message = change_password(self.current_username, new_pw.get())
            if success:
                messagebox.showinfo("Success", message)
                for e in [current_pw, new_pw, confirm_pw]:
                    e.delete(0, tk.END)
            else:
                messagebox.showerror("Error", message)

        ttk.Button(pw_frame, text="Change Password", command=change_pw).grid(
            row=3, column=1, pady=10, sticky="e")

        ttk.Separator(settings_frame, orient="horizontal").pack(fill="x", pady=20)
        ttk.Button(settings_frame, text="🚪 Logout", command=self.logout, width=20).pack(pady=10)

        ttk.Separator(settings_frame, orient="horizontal").pack(fill="x", pady=20)
        ttk.Label(settings_frame,
                  text="Employment Agent System v2.0\n✓ Bcrypt hashing  ✓ CV management  ✓ Validation  ✓ Account lockout",
                  font=("Arial", 9), foreground="gray", justify="left").pack(pady=10)


def main():
    root = tk.Tk()
    app = App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
