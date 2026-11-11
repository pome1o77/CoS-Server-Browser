# Creatures of Sonaria Server Browser

A free Windows application for browsing public servers in **Creatures of Sonaria**.

## Features

- Browse public servers in Trade Realm, Hardcore Realm, and Main Realm.
- Sort servers by:
  - Fewest players
  - Most players
  - Lowest ping
- Automatic sorting preferences for each Realm:
  - Trade Realm: Most players
  - Hardcore Realm: Fewest players
  - Main Realm: Fewest players
- Copy server IDs to the clipboard.
- Join a selected server directly through the Roblox launcher.
- Automatic retry handling for Roblox API rate limits.
- Server data caching to reduce unnecessary API requests.

## Download

Download the latest Windows executable from the [Releases](../../releases) section.

No Python installation is required to run the executable.

## Requirements

- Windows 10 or Windows 11.
- Roblox installed.
- An active internet connection.

## Usage

1. Download `CoS_Server_Browser.zip` from the latest Release.
2. Run `CoS_Server_Browser.exe`.
3. Select Trade Realm, Hardcore Realm, or Main Realm.
4. Choose your preferred sorting option.
5. Double-click a server or select it and click **Join selected**.
6. Use **Copy server ID** to copy a server's ID.

## Notes

- The application retrieves up to 100 public servers per request.
- Roblox API rate limits may temporarily prevent server list updates.
- A minimum refresh interval of 20 seconds is enforced.
- Server results are cached for 60 seconds unless manually refreshed.

## Built With

- Python
- Tkinter
- Roblox Games API
- PyInstaller

## License

See the repository's license information.
