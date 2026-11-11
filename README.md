# Creatures of Sonaria Server Browser

A lightweight Windows application for browsing public servers in **Creatures of Sonaria** (Roblox).

## Features

- Browse public servers in Trade Realm and Hardcore Realm.
- Sort servers by:
  - Fewest players
  - Most players
  - Lowest ping
  - Highest FPS
- Filter servers by maximum player count.
- Filter servers by minimum available slots.
- Copy server IDs to the clipboard.
- Join a selected server directly through the Roblox launcher.
- Automatic retry handling for Roblox API rate limits.

## Download

Download the latest Windows executable from the [Releases](../../releases) section.

No Python installation is required to run the executable.

## Requirements

- Windows 10 or Windows 11.
- Roblox installed.
- An active internet connection.

## Usage

1. Download `CoS_Server_Browser.zip` from Releases.
2. Run the `CoS_Server_Browser.exe`.
3. Select Trade Realm or Hardcore Realm.
4. Choose your preferred sorting and filtering options.
5. Double-click a server or select it and click **Join selected**.

## Notes

- The application currently retrieves only the first page of public servers (up to 100 servers).
- Roblox API rate limits may temporarily prevent server list updates.
- A minimum refresh interval of 20 seconds is enforced.

## Built With

- Python
- Tkinter
- Roblox Games API
- PyInstaller

## License

See the repository's license information.
