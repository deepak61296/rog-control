#!/bin/bash

set -eu

if [ "$EUID" -ne 0 ]; then
  echo "Please run this script with sudo:"
  echo "sudo bash install_nopasswd.sh"
  exit 1
fi

USER_NAME=${SUDO_USER:-$USER}
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

cat << EOF > /etc/sudoers.d/rog-control
# Passwordless sudo rules for ROG Control
$USER_NAME ALL=(ALL) NOPASSWD: /usr/bin/true, /usr/bin/install -d -m 0755 /etc/rog-control, /usr/bin/cat /etc/rog-control/profile.json, /usr/bin/tee /etc/rog-control/profile.json.tmp, /usr/bin/chmod 0644 /etc/rog-control/profile.json.tmp, /usr/bin/mv /etc/rog-control/profile.json.tmp /etc/rog-control/profile.json, /usr/bin/tee /sys/devices/system/cpu/*/cpufreq/scaling_max_freq, /usr/bin/tee /sys/devices/system/cpu/*/cpufreq/scaling_governor, /usr/local/bin/ryzenadj, /usr/bin/ryzenadj
EOF

chmod 0440 /etc/sudoers.d/rog-control

sed "s|@PROJECT_DIR@|$SCRIPT_DIR|g" "$SCRIPT_DIR/rog-control.service" > /etc/systemd/system/rog-control.service
chmod 0644 /etc/systemd/system/rog-control.service
systemctl daemon-reload
systemctl enable --now rog-control.service

echo "Successfully installed sudo rules for $USER_NAME."
echo "ROG Control can now save profiles, apply supported controls, and restore the saved profile after reboot."
