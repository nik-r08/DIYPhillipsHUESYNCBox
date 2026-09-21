# Flashable image

`build.sh` wraps pi-gen (the official Raspberry Pi OS image builder, actively maintained as of 2026-09-16) with one extra stage that runs `installer/install.sh` inside the image. Before building, copy this repository into `image/pi-gen-stage/00-syncbox/files/repo` (pi-gen exposes `files/` to the chroot as `/files`):

```bash
rsync -a --exclude .git --exclude image/work ../ image/pi-gen-stage/00-syncbox/files/repo/
./image/build.sh
```

Label: UNT. The stage layout follows pi-gen's documented conventions (`prerun.sh`, `NN-packages`, `NN-run-chroot.sh`, `EXPORT_IMAGE`) but the build has not been run in this project. The newer `rpi-image-gen` tool is the Raspberry Pi recommendation for production images; migrating to it is a follow-up.
