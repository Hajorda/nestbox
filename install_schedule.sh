#!/bin/bash
# Turn the twice-daily automatic run ON (08:30 and 18:30) or OFF (macOS):   ./install_schedule.sh on|off
D="$(cd "$(dirname "$0")" && pwd)"; L="com.nestbox.scheduler"; P="$HOME/Library/LaunchAgents/$L.plist"
case "$1" in
  on)
    mkdir -p "$HOME/Library/LaunchAgents"
    cat > "$P" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$L</string>
  <key>ProgramArguments</key><array><string>$D/run_scheduled.sh</string></array>
  <key>StartCalendarInterval</key><array>
    <dict><key>Hour</key><integer>8</integer><key>Minute</key><integer>30</integer></dict>
    <dict><key>Hour</key><integer>18</integer><key>Minute</key><integer>30</integer></dict>
  </array>
  <key>EnvironmentVariables</key><dict><key>PATH</key><string>$(dirname "$(command -v python3)"):/usr/local/bin:/usr/bin:/bin</string></dict>
</dict></plist>
PLIST
    launchctl bootstrap "gui/$(id -u)" "$P" && echo "scheduled: 08:30 and 18:30 daily";;
  off)
    for l in "$L" com.hajorda.flatfinder; do launchctl bootout "gui/$(id -u)" "$HOME/Library/LaunchAgents/$l.plist" 2>/dev/null; rm -f "$HOME/Library/LaunchAgents/$l.plist"; done
    echo "schedule removed";;
  *) echo "usage: $0 on|off"; exit 1;;
esac
