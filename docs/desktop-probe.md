# Desktop Environment & Wayland Probe Report

**Date:** 2026-11-15 19:08:34  
**Host Architecture:** Legion Pro 5 (Ubuntu 26.04.1 LTS, GNOME 50.1 Wayland, Kernel 7.0.0-43-generic)

---

## 1. Session & Display Server
| Property | Value | Status |
|---|---|---|
| **XDG_SESSION_TYPE** | `wayland` | Wayland Native |
| **WAYLAND_DISPLAY** | `wayland-0` | Active |
| **XDG_CURRENT_DESKTOP** | `ubuntu:GNOME` | GNOME 50.1 |
| **DESKTOP_SESSION** | `ubuntu` | Active |

---

## 2. Monitor & Layout Configuration
- **Mutter DisplayConfig:** `Available (org.gnome.Mutter.DisplayConfig)`
- **Connected Displays:**
  - **eDP-1 (Built-in OLED Display):** Resolution `2560x1600`, Scale `1.33333x` (Fractional scaling active)
  - **External Monitor (Secondary SWK 27"):** Resolution `1920x1080`, Scale `1.0x` (Fractional scaling active)

---

## 3. AT-SPI Accessibility Bus (`org.a11y.Bus`)
- **Status:** `Available`
- **Bus Socket Address:** `s "unix:path=/run/user/1000/at-spi/bus,guid=5594acf6764772643a75a8a66af94c1d"`
- **Active Accessible Processes:** 11 detected
  - Applications: gnome-shell, at-spi2-registr, ayugram, chrome, warp-taskbar, antigravity, evolution-alarm, xdg-desktop-por, busctl, ibus-extension-

---

## 4. XDG Desktop Portals
- **Desktop Portal (`org.freedesktop.portal.Desktop`):** `Active`
- **GNOME Portal (`org.freedesktop.impl.portal.desktop.gnome`):** `Active`
- **GTK Portal (`org.freedesktop.impl.portal.desktop.gtk`):** `Active`

---

## 5. Window List & Desktop Actuation Feasibility
- **Direct `org.gnome.Shell.Introspect.GetWindows`:** `` (Standard Wayland security sandbox restriction).
- **Primary Screen Understanding:** AT-SPI application accessibility tree + window tracking via AT-SPI `:1.0` (gnome-shell accessible root).
- **Actuation Strategy:** Input injection via XDG Desktop Portal `RemoteDesktop` / `ydotool` / AT-SPI actions.
- **Security Guardrail:** PolicyEngine YELLOW tier confirmation required for all click and typing operations.
