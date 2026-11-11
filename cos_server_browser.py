
import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone


REALMS = {
    "Trade Realm": 14119723130,
    "Hardcore Realm": 136015760267602,
    "Main Realm": 5233782396,
}

MAX_PAGES = 2
PAGE_SIZE = 100
MAX_SERVERS = 100
MAX_RETRIES = 5
CACHE_TTL = 60
MIN_REFRESH_INTERVAL = 20


# =========================
# FONT AND COLOR SETTINGS
# =========================

FONT_FAMILY = "Segoe UI"

FONT_TITLE = (FONT_FAMILY, 20, "bold")
FONT_NORMAL = (FONT_FAMILY, 11)
FONT_STATUS = (FONT_FAMILY, 10)
FONT_TABLE = (FONT_FAMILY, 11)
FONT_BUTTON = (FONT_FAMILY, 11)

STATUS_COLOR = "#527DA8"
WARNING_COLOR = "#C45A5A"


def retry_delay(error, attempt):
    """Determine a respectful delay before retrying."""
    retry_after = error.headers.get("Retry-After")

    if retry_after:
        try:
            return min(max(float(retry_after), 1), 120)
        except ValueError:
            try:
                retry_date = parsedate_to_datetime(retry_after)
                return min(max(
                    (retry_date - datetime.now(timezone.utc)).total_seconds(),
                    1
                ), 120)
            except (ValueError, TypeError):
                pass

    return min(3 * (2 ** attempt), 60)


def fetch_servers(place_id, sort_order="Asc", max_pages=MAX_PAGES):
    """Fetch public servers using Roblox's server-side sorting."""
    api_url = f"https://games.roblox.com/v1/games/{place_id}/servers/Public"

    servers = []
    cursor = None

    for _ in range(max_pages):
        if len(servers) >= MAX_SERVERS:
            break

        params = {
            "sortOrder": sort_order,
            "excludeFullGames": "false",
            "limit": str(PAGE_SIZE),
        }

        if cursor:
            params["cursor"] = cursor

        request = urllib.request.Request(
            api_url + "?" + urllib.parse.urlencode(params),
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json",
            },
        )

        for attempt in range(MAX_RETRIES + 1):
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                break

            except urllib.error.HTTPError as error:
                if error.code == 429:
                    if attempt == MAX_RETRIES:
                        raise RuntimeError(
                            "Roblox is still rate-limiting requests. "
                            "Please wait before trying again."
                        )

                    time.sleep(retry_delay(error, attempt))

                elif error.code in (500, 502, 503, 504):
                    if attempt == MAX_RETRIES:
                        raise

                    time.sleep(min(3 * (2 ** attempt), 60))

                else:
                    raise

        servers.extend(payload.get("data", []))
        servers = servers[:MAX_SERVERS]
        cursor = payload.get("nextPageCursor")

        if not cursor or len(servers) >= MAX_SERVERS:
            break

    return servers


class ServerBrowser(tk.Tk):

    def __init__(self):
        super().__init__()

        self.title("CoS Server Browser")
        self.geometry("900x580")
        self.minsize(700, 450)

        self.servers = []
        self.visible_servers = []
        self.loaded_place_id = REALMS["Trade Realm"]
        self.last_refresh = 0
        self.loading = False
        self.server_cache = {}

        self.realm_var = tk.StringVar(value="Trade Realm")

        self._configure_styles()
        self._build_ui()
        self.refresh_servers()

    def _configure_styles(self):
        style = ttk.Style(self)

        style.configure(".", font=FONT_NORMAL)
        style.configure(
            "Treeview",
            font=FONT_TABLE,
            rowheight=27,
        )
        style.configure(
            "Treeview.Heading",
            font=(FONT_FAMILY, 11, "bold"),
        )
        style.configure(
            "TButton",
            font=FONT_BUTTON,
            padding=(8, 5),
        )
        style.configure(
            "TCombobox",
            font=FONT_NORMAL,
            padding=4,
        )
        style.configure(
            "Status.TLabel",
            font=FONT_STATUS,
            foreground=STATUS_COLOR,
        )
        style.configure(
            "Warning.TLabel",
            font=FONT_STATUS,
            foreground=WARNING_COLOR,
        )

    def _set_status(self, message, warning=False):
        self.status_var.set(message)
        self.status_label.configure(
            style="Warning.TLabel" if warning else "Status.TLabel"
        )

    def _build_ui(self):
        outer = ttk.Frame(self, padding=14)
        outer.pack(fill="both", expand=True)

        # Header
        header = ttk.Frame(outer)
        header.pack(fill="x")

        header_text = ttk.Frame(header)
        header_text.pack(side="left", fill="x", expand=True)

        ttk.Label(
            header_text,
            text="CoS Server Browser",
            font=FONT_TITLE,
        ).pack(anchor="w", pady=(0, 8))

        self.status_var = tk.StringVar(value="Initializing...")

        self.status_label = ttk.Label(
            header_text,
            textvariable=self.status_var,
            style="Status.TLabel",
        )
        self.status_label.pack(anchor="w", pady=(4, 0))

        self.refresh_button = ttk.Button(
            header,
            text="Refresh",
            command=lambda: self.refresh_servers(bypass_cache=True),
        )
        self.refresh_button.pack(side="right", padx=(10, 0))

        # Controls
        controls = ttk.Frame(outer)
        controls.pack(fill="x", pady=(18, 12))

        ttk.Label(controls, text="Realm:").pack(side="left")

        self.realm_box = ttk.Combobox(
            controls,
            textvariable=self.realm_var,
            values=list(REALMS.keys()),
            state="readonly",
            width=16,
        )
        self.realm_box.pack(side="left", padx=7)
        self.realm_box.bind(
            "<<ComboboxSelected>>",
            self._on_realm_changed,
        )

        ttk.Label(
            controls,
            text="Sort by:",
        ).pack(side="left", padx=(14, 0))

        self.sort_var = tk.StringVar(value="Most players")

        self.sort_box = ttk.Combobox(
            controls,
            textvariable=self.sort_var,
            values=["Most players", "Fewest players", "Lowest ping"],
            state="readonly",
            width=17,
        )
        self.sort_box.pack(side="left", padx=7)
        self.sort_box.bind(
            "<<ComboboxSelected>>",
            lambda event: self.refresh_servers(force=True),
        )

        # Server table
        columns = ("players", "ping", "server_id")

        self.tree = ttk.Treeview(
            outer,
            columns=columns,
            show="headings",
            height=20,
        )

        headings = {
            "players": ("Players", 100, "center"),
            "ping": ("Ping (ms)", 100, "center"),
            "server_id": ("Server ID", 500, "w"),
        }

        for column, (title, width, anchor) in headings.items():
            self.tree.heading(column, text=title)
            self.tree.column(column, width=width, anchor=anchor)

        scrollbar = ttk.Scrollbar(
            outer,
            orient="vertical",
            command=self.tree.yview,
        )

        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="left", fill="y")

        self.tree.bind(
            "<Double-1>",
            lambda event: self.join_selected(),
        )

        # Action buttons
        right = ttk.Frame(outer)
        right.pack(side="right", fill="y", padx=(12, 0))

        ttk.Button(
            right,
            text="Join selected",
            command=self.join_selected,
        ).pack(fill="x", pady=(0, 9))

        ttk.Button(
            right,
            text="Copy server ID",
            command=self.copy_selected,
        ).pack(fill="x")

        ttk.Label(
            right,
            text="Double-click a server\nto join it.",
            justify="left",
            font=FONT_NORMAL,
        ).pack(anchor="w", pady=(16, 0))

    def _on_realm_changed(self, event=None):
        realm = self.realm_var.get()

        self.sort_var.set(
            "Most players" if realm == "Trade Realm" else "Fewest players"
        )

        self.refresh_servers(force=True)

    def _set_controls_enabled(self, enabled):
        state = "readonly" if enabled else "disabled"

        self.refresh_button.configure(
            state="normal" if enabled else "disabled"
        )
        self.realm_box.configure(state=state)
        self.sort_box.configure(state=state)

    def refresh_servers(self, force=False, bypass_cache=False):
        if self.loading:
            return

        place_id = REALMS[self.realm_var.get()]
        realm = self.realm_var.get()
        sort_mode = self.sort_var.get()

        sort_order = "Desc" if sort_mode == "Most players" else "Asc"

        cache_key = (place_id, sort_order)
        now = time.monotonic()
        cached = self.server_cache.get(cache_key)

        # Use fresh cached data unless Refresh was explicitly pressed.
        if not bypass_cache and cached:
            cache_age = now - cached["timestamp"]

            if cache_age < CACHE_TTL:
                self.servers = cached["data"]
                self.loaded_place_id = place_id
                self.apply_filters()

                remaining = int(CACHE_TTL - cache_age)

                self._set_status(
                    f"Loaded {len(self.servers)} servers from cache. "
                    f"Cache expires in {remaining} seconds."
                )
                return

        if not force:
            remaining = MIN_REFRESH_INTERVAL - (now - self.last_refresh)

            if remaining > 0:
                self._set_status(
                    f"Please wait {int(remaining) + 1} seconds "
                    "before refreshing again.",
                    warning=True,
                )
                return

        self.loading = True
        self.last_refresh = now
        self._set_controls_enabled(False)
        self._set_status(f"Loading {realm} servers...")

        threading.Thread(
            target=self._load_worker,
            args=(place_id, sort_order),
            daemon=True,
        ).start()

    def _load_worker(self, place_id, sort_order):
        try:
            data = fetch_servers(place_id, sort_order=sort_order)

            self.after(
                0,
                lambda: self._load_success(data, place_id, sort_order),
            )

        except urllib.error.HTTPError as error:
            detail = f"Roblox API returned HTTP {error.code}."

            self.after(
                0,
                lambda: self._load_error(detail, place_id, sort_order),
            )

        except Exception as error:
            detail = str(error)

            self.after(
                0,
                lambda: self._load_error(detail, place_id, sort_order),
            )

    def _load_success(self, data, place_id, sort_order):
        self.servers = data
        self.loaded_place_id = place_id
        self.loading = False

        self.server_cache[(place_id, sort_order)] = {
            "data": data,
            "timestamp": time.monotonic(),
        }

        self._set_controls_enabled(True)
        self.apply_filters()
        self._set_status(f"Loaded {len(data)} servers.")

    def _load_error(self, detail, place_id, sort_order):
        self.loading = False
        self._set_controls_enabled(True)

        cached = self.server_cache.get((place_id, sort_order))

        if cached:
            self.servers = cached["data"]
            self.loaded_place_id = place_id
            self.apply_filters()

            age = int(time.monotonic() - cached["timestamp"])

            self._set_status(
                f"Could not refresh servers. "
                f"Showing cached results ({age} seconds old).",
                warning=True,
            )
            return

        self._set_status(
            f"Could not load servers: {detail}",
            warning=True,
        )

        messagebox.showerror(
            "Server list error",
            f"{detail}\n\nWait a little before trying again.",
        )

    def apply_filters(self):
        filtered = list(self.servers)
        sort_mode = self.sort_var.get()

        if sort_mode == "Most players":
            filtered.sort(
                key=lambda server: int(server.get("playing", 0)),
                reverse=True,
            )

        elif sort_mode == "Fewest players":
            filtered.sort(
                key=lambda server: int(server.get("playing", 0)),
            )

        elif sort_mode == "Lowest ping":
            filtered.sort(
                key=lambda server: server.get("ping") or 999999,
            )

        self.visible_servers = filtered

        for item in self.tree.get_children():
            self.tree.delete(item)

        for server in filtered:
            self.tree.insert(
                "",
                "end",
                iid=server["id"],
                values=(
                    f'{server.get("playing", 0)}/'
                    f'{server.get("maxPlayers", 0)}',
                    server.get("ping", "—"),
                    server["id"],
                ),
            )

    def _selected_server_id(self):
        selection = self.tree.selection()

        if not selection:
            messagebox.showinfo(
                "Select a server",
                "Select a server first.",
            )
            return None

        return selection[0]

    def join_selected(self):
        server_id = self._selected_server_id()

        if not server_id:
            return

        launch_url = (
            f"roblox://experiences/start?"
            f"placeId={self.loaded_place_id}"
            f"&gameInstanceId={urllib.parse.quote(server_id)}"
        )

        try:
            webbrowser.open(launch_url)
            self._set_status("Sent join request to Roblox launcher.")

        except Exception as error:
            messagebox.showerror(
                "Could not launch Roblox",
                str(error),
            )

    def copy_selected(self):
        server_id = self._selected_server_id()

        if not server_id:
            return

        self.clipboard_clear()
        self.clipboard_append(server_id)
        self._set_status("Server ID copied to clipboard.")


if __name__ == "__main__":
    app = ServerBrowser()
    app.mainloop()
