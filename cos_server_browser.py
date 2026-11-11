
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
}

MAX_PAGES = 1
MAX_RETRIES = 5
MIN_REFRESH_INTERVAL = 20


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

    return min(5 * (2 ** attempt), 60)


def fetch_servers(place_id, max_pages=MAX_PAGES):
    """Fetch public servers with rate-limit handling."""
    api_url = (
        f"https://games.roblox.com/v1/games/"
        f"{place_id}/servers/Public"
    )

    servers = []
    cursor = None

    for page in range(max_pages):
        params = {
            "sortOrder": "Asc",
            "excludeFullGames": "true",
            "limit": "100",
        }

        if cursor:
            params["cursor"] = cursor

        url = api_url + "?" + urllib.parse.urlencode(params)

        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json",
            },
        )

        for attempt in range(MAX_RETRIES + 1):
            try:
                with urllib.request.urlopen(
                    request, timeout=30
                ) as response:
                    payload = json.loads(
                        response.read().decode("utf-8")
                    )
                break

            except urllib.error.HTTPError as error:
                if error.code == 429:
                    if attempt == MAX_RETRIES:
                        raise RuntimeError(
                            "Roblox is still rate-limiting requests. "
                            "Please wait a few minutes before trying again."
                        )

                    delay = retry_delay(error, attempt)
                    time.sleep(delay)

                elif error.code in (500, 502, 503, 504):
                    if attempt == MAX_RETRIES:
                        raise

                    time.sleep(min(5 * (2 ** attempt), 60))

                else:
                    raise

        servers.extend(payload.get("data", []))
        cursor = payload.get("nextPageCursor")

        if not cursor:
            break

    return servers


class ServerBrowser(tk.Tk):

    def __init__(self):
        super().__init__()

        self.title("Creatures of Sonaria — Server Browser")
        self.geometry("900x580")
        self.minsize(700, 450)

        self.servers = []
        self.visible_servers = []
        self.loaded_place_id = REALMS["Trade Realm"]
        self.last_refresh = 0
        self.loading = False

        self.realm_var = tk.StringVar(value="Trade Realm")

        self._build_ui()
        self.refresh_servers()

    def _build_ui(self):
        outer = ttk.Frame(self, padding=12)
        outer.pack(fill="both", expand=True)

        header = ttk.Frame(outer)
        header.pack(fill="x")

        ttk.Label(
            header,
            text="Creatures of Sonaria — Server Browser",
            font=("Segoe UI", 16, "bold"),
        ).pack(side="left")

        self.refresh_button = ttk.Button(
            header,
            text="Refresh",
            command=self.refresh_servers,
        )
        self.refresh_button.pack(side="right")

        controls = ttk.Frame(outer)
        controls.pack(fill="x", pady=(16, 10))

        ttk.Label(controls, text="Realm:").pack(side="left")

        self.realm_box = ttk.Combobox(
            controls,
            textvariable=self.realm_var,
            values=list(REALMS.keys()),
            state="readonly",
            width=16,
        )
        self.realm_box.pack(side="left", padx=6)
        self.realm_box.bind(
            "<<ComboboxSelected>>",
            lambda event: self.refresh_servers(force=True),
        )

        ttk.Label(controls, text="Sort by:").pack(
            side="left", padx=(12, 0)
        )

        self.sort_var = tk.StringVar(value="Fewest players")

        sort_box = ttk.Combobox(
            controls,
            textvariable=self.sort_var,
            values=[
                "Fewest players",
                "Most players",
                "Lowest ping",
                "Highest FPS",
            ],
            state="readonly",
            width=17,
        )
        sort_box.pack(side="left", padx=6)
        sort_box.bind(
            "<<ComboboxSelected>>",
            lambda event: self.apply_filters(),
        )

        ttk.Label(controls, text="Max players:").pack(
            side="left", padx=(8, 0)
        )

        self.max_players_var = tk.StringVar(value="Any")

        max_box = ttk.Combobox(
            controls,
            textvariable=self.max_players_var,
            values=["Any", "10", "20", "30", "50", "75"],
            state="readonly",
            width=7,
        )
        max_box.pack(side="left", padx=6)
        max_box.bind(
            "<<ComboboxSelected>>",
            lambda event: self.apply_filters(),
        )

        ttk.Label(controls, text="Min free slots:").pack(
            side="left", padx=(8, 0)
        )

        self.free_slots_var = tk.StringVar(value="1")

        free_box = ttk.Combobox(
            controls,
            textvariable=self.free_slots_var,
            values=["0", "1", "5", "10", "20"],
            state="readonly",
            width=5,
        )
        free_box.pack(side="left", padx=6)
        free_box.bind(
            "<<ComboboxSelected>>",
            lambda event: self.apply_filters(),
        )

        columns = ("players", "ping", "fps", "server_id")

        self.tree = ttk.Treeview(
            outer,
            columns=columns,
            show="headings",
            height=20,
        )

        self.tree.heading("players", text="Players")
        self.tree.heading("ping", text="Ping (ms)")
        self.tree.heading("fps", text="FPS")
        self.tree.heading("server_id", text="Server ID")

        self.tree.column("players", width=90, anchor="center")
        self.tree.column("ping", width=90, anchor="center")
        self.tree.column("fps", width=80, anchor="center")
        self.tree.column("server_id", width=500, anchor="w")

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

        right = ttk.Frame(outer)
        right.pack(side="right", fill="y", padx=(10, 0))

        ttk.Button(
            right,
            text="Join selected",
            command=self.join_selected,
        ).pack(fill="x", pady=(0, 8))

        ttk.Button(
            right,
            text="Copy server ID",
            command=self.copy_selected,
        ).pack(fill="x")

        ttk.Label(
            right,
            text="Double-click a server\nto join it.",
            justify="left",
        ).pack(anchor="w", pady=(14, 0))

        self.status_var = tk.StringVar(
            value="Initializing..."
        )

        ttk.Label(
            outer,
            textvariable=self.status_var,
        ).pack(side="bottom", anchor="w", pady=(10, 0))

    def refresh_servers(self, force=False):
        if self.loading:
            return

        now = time.monotonic()

        if not force:
            remaining = MIN_REFRESH_INTERVAL - (
                now - self.last_refresh
            )

            if remaining > 0:
                self.status_var.set(
                    f"Please wait {int(remaining) + 1} seconds "
                    "before refreshing again."
                )
                return

        self.loading = True
        self.last_refresh = now

        self.refresh_button.configure(state="disabled")
        self.realm_box.configure(state="disabled")

        place_id = REALMS[self.realm_var.get()]
        realm = self.realm_var.get()

        self.status_var.set(
            f"Loading {realm} servers..."
        )

        threading.Thread(
            target=self._load_worker,
            args=(place_id,),
            daemon=True,
        ).start()

    def _load_worker(self, place_id):
        try:
            data = fetch_servers(place_id)
            self.after(
                0,
                lambda: self._load_success(data, place_id),
            )

        except urllib.error.HTTPError as error:
            detail = f"Roblox API returned HTTP {error.code}."
            self.after(
                0,
                lambda: self._load_error(detail),
            )

        except Exception as error:
            detail = str(error)
            self.after(
                0,
                lambda: self._load_error(detail),
            )

    def _load_success(self, data, place_id):
        self.servers = data
        self.loaded_place_id = place_id
        self.loading = False

        self.refresh_button.configure(state="normal")
        self.realm_box.configure(state="readonly")

        self.apply_filters()

        self.status_var.set(
            f"Loaded {len(data)} servers. "
            "Only the first page was requested."
        )

    def _load_error(self, detail):
        self.loading = False

        self.refresh_button.configure(state="normal")
        self.realm_box.configure(state="readonly")

        self.status_var.set("Could not load servers.")

        messagebox.showerror(
            "Server list error",
            f"{detail}\n\n"
            "Wait a little before trying again.",
        )

    def apply_filters(self):
        max_filter = self.max_players_var.get()
        min_free = int(self.free_slots_var.get())

        filtered = []

        for server in self.servers:
            playing = int(server.get("playing", 0))
            capacity = int(server.get("maxPlayers", 0))

            if max_filter != "Any":
                if capacity > int(max_filter):
                    continue

            if capacity - playing < min_free:
                continue

            filtered.append(server)

        sort_mode = self.sort_var.get()

        if sort_mode == "Fewest players":
            filtered.sort(
                key=lambda s: s.get("playing", 0)
            )

        elif sort_mode == "Most players":
            filtered.sort(
                key=lambda s: s.get("playing", 0),
                reverse=True,
            )

        elif sort_mode == "Lowest ping":
            filtered.sort(
                key=lambda s: s.get("ping") or 999999
            )

        elif sort_mode == "Highest FPS":
            filtered.sort(
                key=lambda s: s.get("fps") or 0,
                reverse=True,
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
                    server.get("fps", "—"),
                    server["id"],
                ),
            )

        self.status_var.set(
            f"Showing {len(filtered)} of "
            f"{len(self.servers)} loaded servers."
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
            self.status_var.set(
                "Sent join request to Roblox launcher."
            )

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

        self.status_var.set(
            "Server ID copied to clipboard."
        )


if __name__ == "__main__":
    app = ServerBrowser()
    app.mainloop()
