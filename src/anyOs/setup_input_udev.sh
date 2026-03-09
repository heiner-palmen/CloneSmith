#!/usr/bin/env bash
set -euo pipefail

# setup_input_udev.sh
# Create udev rules that grant the 'input' group access to input devices
# and add the specified user (or the sudo user) to that group.

if [ "$(id -u)" -ne 0 ]; then
  echo "This script must be run with sudo. Usage: sudo ./setup_input_udev.sh [username]" >&2
  exit 1
fi

USER_TO_ADD=${1:-${SUDO_USER:-$(logname 2>/dev/null || echo "$USER")}}
GROUP=input
RULE_FILE=/etc/udev/rules.d/99-clonehero-input.rules

echo "Creating group '$GROUP' if it does not exist..."
if ! getent group "$GROUP" >/dev/null; then
  groupadd "$GROUP"
fi

echo "Writing udev rule to $RULE_FILE"
cat > "$RULE_FILE" <<'EOF'
KERNEL=="uinput", MODE="0660", GROUP="input"
KERNEL=="event*", SUBSYSTEM=="input", MODE="0660", GROUP="input"
EOF

echo "Reloading udev rules..."
udevadm control --reload
udevadm trigger || true

echo "Adding user '$USER_TO_ADD' to group '$GROUP'..."
usermod -aG "$GROUP" "$USER_TO_ADD"

echo "Adjusting existing device nodes (best-effort)..."
for dev in /dev/uinput /dev/input/event*; do
  if [ -e "$dev" ]; then
    chgrp "$GROUP" "$dev" || true
    chmod 660 "$dev" || true
  fi
done

echo
echo "Done. The user '$USER_TO_ADD' was added to group '$GROUP'."
echo "Log out and log back in (or reboot) for the group change to take effect."
