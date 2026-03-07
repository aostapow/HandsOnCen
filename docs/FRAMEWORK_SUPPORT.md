# Framework Support Reference

How HandsOn works with different UI toolkits on Windows.

## Support Matrix

| Framework | UIA Support | find_element | list_elements | OCR needed? | Configuration |
|-----------|------------|-------------|--------------|------------|---------------|
| Qt5/Qt6 (QWidget) | Partial | Standard widgets | Standard widgets | Custom widgets, QML | None |
| Qt Quick / QML | Poor | Only with Accessible{} | Limited | Most content | None |
| WPF | Full | All controls | All controls | Custom canvas only | None |
| WinForms (.NET 5+) | Good | Standard controls | Standard controls | Owner-drawn | None |
| Electron (with flag) | Good | ARIA-mapped elements | ARIA-mapped | Canvas content | `--force-renderer-accessibility` |
| Electron (no flag) | None | Nothing | Nothing | Everything | Enable flag |
| Win32 / MFC | Partial | Common Controls | Common Controls | Owner-drawn | None |
| Java Swing | None (UIA) | Not via UIA | Not via UIA | Primary method | `jabswitch -enable` for JAB |
| JavaFX | Full | Standard controls | Standard controls | Canvas, WebView | None |
| GTK on Windows | None | Nothing | Nothing | Everything | None available |
| UWP / WinUI | Full | XAML controls | XAML controls | Custom canvas only | None |
| Chromium browsers | Conditional | Page elements | Page elements | Canvas/WebGL | None |

## Framework Details

### Qt5 / Qt6 (PySide6, PyQt)
**What works:** QPushButton, QLineEdit, QComboBox, QSpinBox, QCheckBox, QRadioButton, QTabWidget, QListView, QTreeView, QTableView, QMenuBar, QProgressBar, QSlider.

**What doesn't:** Custom QWidget subclasses without `QAccessibleInterface`, QML items without `Accessible {}` blocks, QOpenGLWidget content.

**Tip:** `find_element` works for all standard widgets. Use OCR for custom-painted areas.

### WPF (.NET)
**What works:** Everything. WPF has the most complete UIA support. Use `AutomationId` (from `x:Name`) for the most reliable selectors.

**What doesn't:** Custom controls without `AutomationPeer`, virtualized list items outside viewport (scroll first), canvas-drawn content.

### WinForms (.NET)
**What works:** All standard controls on .NET 5+ and .NET Framework 4.7.1+.

**What doesn't:** Owner-drawn controls, UserControls without `CreateAccessibilityInstance()` override, older .NET Framework DataGridView cells.

### Electron (VS Code, Slack, Discord, Teams)
**What works:** All ARIA-role-mapped HTML elements when accessibility is enabled.

**What doesn't:** Anything when the flag is missing. Canvas content (Monaco editor, graphs). Virtual scroll items outside viewport.

**Configuration:** Launch with `--force-renderer-accessibility`. Some apps auto-enable when a screen reader is detected.

### Win32 / MFC
**What works:** Standard Common Controls library widgets (buttons, lists, trees, tabs, toolbars, edit controls).

**What doesn't:** Owner-drawn controls (`BS_OWNERDRAW`), custom HWND classes, Ribbon UI (partially accessible). Menus only accessible while open.

### Java Swing
**UIA does not work.** Swing uses Java Access Bridge (JAB), a separate accessibility API. Enable with `jabswitch -enable`.

**Primary automation approach:** OCR + coordinate-based clicking. For full programmatic access, use JAB-aware tools.

### JavaFX
**What works:** All standard JavaFX controls have native UIA providers.

**What doesn't:** Canvas-drawn nodes, WebView content.

### GTK on Windows (GIMP, Inkscape)
**No UIA support.** The ATK-to-UIA bridge is non-functional on Windows.

**Only approach:** OCR + coordinate-based automation. Use `screenshot(region)` to read content, `click(x, y)` to interact.

### UWP / WinUI (Windows Store apps, Settings)
**What works:** All XAML controls have full UIA support. Use `AutomationId` for reliable targeting.

**What doesn't:** Custom canvas or DirectX content. Flyout menus may appear as separate top-level windows — use `list_windows` to find them.

### Chromium Browsers (Chrome, Edge, Brave, Vivaldi)
**What works:** Standard page elements via the accessibility tree.

**What doesn't:** Canvas/WebGL content, highly dynamic virtual-scroll content.

**Note:** HandsOn distinguishes browsers from Electron apps automatically by process name. Both use the `Chrome_WidgetWin_1` window class, but browser processes (chrome.exe, msedge.exe, etc.) are classified as `chromium_browser` while Electron apps (Code.exe, Slack.exe, etc.) are classified as `electron`.

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `list_elements` returns very few items | Tree not deep enough | Try `list_elements(role="Button")` or increase depth |
| `find_element` finds nothing | Wrong framework or accessibility disabled | Run `detect_framework` to check |
| OCR misses text | Image too large (>4096px) or dark background | Automatic: downscale + inversion retry built in |
| Electron app shows only frame | Accessibility flag not set | Relaunch with `--force-renderer-accessibility` |
| Java app completely opaque | JAB not enabled | Run `jabswitch -enable` and restart app |

