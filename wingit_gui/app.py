"""Tkinter UI to browse and install winget applications."""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from .winget_client import WingetError, WingetPackage, fetch_all_packages, filter_packages, install_package


class WingetGui(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Winget App Installer")
        self.geometry("950x600")

        self.packages: list[WingetPackage] = []
        self.filtered_packages: list[WingetPackage] = []
        self.worker_queue: queue.Queue[tuple[str, object]] = queue.Queue()

        self._build_ui()
        self.after(200, self._process_worker_events)
        self._load_packages_async()

    def _build_ui(self) -> None:
        top = ttk.Frame(self, padding=12)
        top.pack(fill=tk.BOTH, expand=True)

        header = ttk.Label(top, text="Browse Winget Packages", font=("Segoe UI", 16, "bold"))
        header.pack(anchor=tk.W)

        subtitle = ttk.Label(
            top,
            text="Type to filter, select a package, and click Install.",
        )
        subtitle.pack(anchor=tk.W, pady=(0, 10))

        search_row = ttk.Frame(top)
        search_row.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(search_row, text="Search:").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_row, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 8))
        search_entry.bind("<KeyRelease>", lambda _evt: self._apply_filter())

        self.refresh_button = ttk.Button(search_row, text="Refresh", command=self._load_packages_async)
        self.refresh_button.pack(side=tk.LEFT)

        columns = ("name", "id", "version", "source")
        self.tree = ttk.Treeview(top, columns=columns, show="headings", height=20)
        self.tree.heading("name", text="Name")
        self.tree.heading("id", text="Package ID")
        self.tree.heading("version", text="Version")
        self.tree.heading("source", text="Source")
        self.tree.column("name", width=320)
        self.tree.column("id", width=320)
        self.tree.column("version", width=120)
        self.tree.column("source", width=100)
        self.tree.pack(fill=tk.BOTH, expand=True)

        btn_row = ttk.Frame(top)
        btn_row.pack(fill=tk.X, pady=(10, 0))

        self.install_button = ttk.Button(btn_row, text="Install Selected App", command=self._install_selected)
        self.install_button.pack(side=tk.LEFT)

        self.status_var = tk.StringVar(value="Loading packages...")
        self.status_label = ttk.Label(btn_row, textvariable=self.status_var)
        self.status_label.pack(side=tk.RIGHT)

    def _set_busy(self, busy: bool, status: str) -> None:
        state = tk.DISABLED if busy else tk.NORMAL
        self.install_button.configure(state=state)
        self.refresh_button.configure(state=state)
        self.status_var.set(status)

    def _load_packages_async(self) -> None:
        self._set_busy(True, "Loading packages from winget...")

        def worker() -> None:
            try:
                packages = fetch_all_packages()
            except Exception as error:  # noqa: BLE001 - pass through to UI handler
                self.worker_queue.put(("load_error", error))
                return
            self.worker_queue.put(("load_success", packages))

        threading.Thread(target=worker, daemon=True).start()

    def _apply_filter(self) -> None:
        self.filtered_packages = filter_packages(self.packages, self.search_var.get())
        self._render_rows()

    def _render_rows(self) -> None:
        self.tree.delete(*self.tree.get_children())
        for package in self.filtered_packages:
            self.tree.insert(
                "",
                tk.END,
                values=(package.name, package.package_id, package.version, package.source),
            )
        self.status_var.set(f"Showing {len(self.filtered_packages)} / {len(self.packages)} apps")

    def _install_selected(self) -> None:
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("No app selected", "Please select an app first.")
            return

        values = self.tree.item(selected[0], "values")
        package_id = values[1]
        self._set_busy(True, f"Installing {package_id}...")

        def worker() -> None:
            try:
                output = install_package(package_id)
            except Exception as error:  # noqa: BLE001 - pass through to UI handler
                self.worker_queue.put(("install_error", (package_id, error)))
                return
            self.worker_queue.put(("install_success", (package_id, output)))

        threading.Thread(target=worker, daemon=True).start()

    def _process_worker_events(self) -> None:
        while True:
            try:
                event_type, payload = self.worker_queue.get_nowait()
            except queue.Empty:
                break

            if event_type == "load_success":
                self.packages = sorted(payload, key=lambda package: package.name.lower())
                self._apply_filter()
                self._set_busy(False, f"Loaded {len(self.packages)} apps")
            elif event_type == "load_error":
                self._set_busy(False, "Could not load apps")
                messagebox.showerror("Winget error", str(payload))
            elif event_type == "install_success":
                package_id, _output = payload
                self._set_busy(False, f"Installed {package_id}")
                messagebox.showinfo("Install complete", f"Installed {package_id} successfully.")
            elif event_type == "install_error":
                package_id, error = payload
                self._set_busy(False, f"Install failed: {package_id}")
                messagebox.showerror("Install failed", f"{package_id}\n\n{error}")

        self.after(200, self._process_worker_events)


def main() -> None:
    try:
        app = WingetGui()
    except WingetError as error:
        raise SystemExit(str(error)) from error
    app.mainloop()


if __name__ == "__main__":
    main()
