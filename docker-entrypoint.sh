#!/bin/sh
set -e

ARTIFACTS_DIR="/app/artifacts"

# Set umask to 027 (files: 0640 rw-r-----, directories: 0750 rwxr-x---)
umask 027

# Check and initialize persistent disk mount point ownership and permissions
if [ -d "$ARTIFACTS_DIR" ]; then
    DIR_UID=$(stat -c '%u' "$ARTIFACTS_DIR" 2>/dev/null || echo "")
    DIR_GID=$(stat -c '%g' "$ARTIFACTS_DIR" 2>/dev/null || echo "")

    # Trigger one-time initialization only on initial root-owned mount.
    # On subsequent restarts where the mount is already owned by pwuser (1001:1001),
    # skip recursive scanning to avoid performance degradation as disk contents grow.
    if [ "$DIR_UID" != "1001" ] || [ "$DIR_GID" != "1001" ]; then
        echo "[entrypoint] Initializing persistent disk at $ARTIFACTS_DIR for pwuser (1001:1001)..."
        chown pwuser:pwuser "$ARTIFACTS_DIR"
        chmod 0750 "$ARTIFACTS_DIR"

        # Safely set permissions and ownership on existing contents without following symlinks:
        # 1. Apply mode 0750 to directories only
        find -P "$ARTIFACTS_DIR" -mindepth 1 -type d -exec chmod 0750 {} +
        # 2. Apply mode 0640 to regular files only
        find -P "$ARTIFACTS_DIR" -mindepth 1 -type f -exec chmod 0640 {} +
        # 3. Change ownership with -h so symlinks themselves are updated, never their targets
        find -P "$ARTIFACTS_DIR" -mindepth 1 -exec chown -h pwuser:pwuser {} +
    else
        # Constant-time permission check on mount directory without disk scan
        chmod 0750 "$ARTIFACTS_DIR"
    fi
fi

# Drop privileges and execute the container command as pwuser (UID 1001, GID 1001)
exec gosu pwuser "$@"
