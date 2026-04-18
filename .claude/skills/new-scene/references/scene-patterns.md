# Scene Patterns Reference

Common UI patterns used across scenes in this engine.

---

## Cursor / Selection Menu

```python
def __init__(self, ...):
    self._items  = ["Option A", "Option B", "Option C"]
    self._cursor = 0

def handle_events(self, events):
    for event in events:
        if event.type != pygame.KEYDOWN:
            continue
        if event.key == pygame.K_UP:
            self._cursor = (self._cursor - 1) % len(self._items)
            if self._sfx_manager: self._sfx_manager.play("cursor")
        elif event.key == pygame.K_DOWN:
            self._cursor = (self._cursor + 1) % len(self._items)
            if self._sfx_manager: self._sfx_manager.play("cursor")
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self._confirm()
            if self._sfx_manager: self._sfx_manager.play("confirm")
        elif event.key == pygame.K_ESCAPE:
            self._on_close()
            if self._sfx_manager: self._sfx_manager.play("cancel")

def _draw_menu(self, screen, x, y, item_h=32):
    for i, label in enumerate(self._items):
        color = C_HEADER if i == self._cursor else C_TEXT
        surf = self._font_body.render(label, True, color)
        screen.blit(surf, (x + 16, y + i * item_h))
        if i == self._cursor:
            pygame.draw.rect(screen, C_BORDER, (x, y + i * item_h - 2, 300, item_h), 1, border_radius=3)
```

---

## Two-Column Layout (label + value)

```python
def _draw_row(self, screen, x, y, label, value, label_color=None, value_color=None):
    lc = label_color or C_MUTED
    vc = value_color or C_TEXT
    ls = self._font_body.render(label, True, lc)
    vs = self._font_body.render(str(value), True, vc)
    screen.blit(ls, (x, y))
    screen.blit(vs, (x + 200, y))   # adjust column width as needed
```

---

## HP / MP Bar

```python
def _draw_bar(self, screen, x, y, current, maximum, color, w=120, h=8):
    pygame.draw.rect(screen, (40, 40, 60), (x, y, w, h), border_radius=3)
    ratio = current / maximum if maximum else 0
    pygame.draw.rect(screen, color, (x, y, int(w * ratio), h), border_radius=3)
```

Colors: HP = `(80, 200, 100)`, MP = `(80, 140, 220)`, EXP = `(200, 160, 60)`

---

## Confirmation Dialog (yes/no)

```python
def __init__(self, ...):
    self._confirm_state = None   # None | "confirm"
    self._confirm_cursor = 0     # 0 = Yes, 1 = No

def _open_confirm(self):
    self._confirm_state  = "confirm"
    self._confirm_cursor = 1   # default to No (safer)

def _handle_confirm_input(self, event):
    if event.key in (pygame.K_LEFT, pygame.K_RIGHT):
        self._confirm_cursor ^= 1
    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
        if self._confirm_cursor == 0:
            self._do_action()
        self._confirm_state = None
    elif event.key == pygame.K_ESCAPE:
        self._confirm_state = None

def _draw_confirm(self, screen, message="Are you sure?"):
    w, h = 320, 100
    x = (screen.get_width()  - w) // 2
    y = (screen.get_height() - h) // 2
    pygame.draw.rect(screen, C_BG,     (x, y, w, h), border_radius=6)
    pygame.draw.rect(screen, C_BORDER, (x, y, w, h), 2, border_radius=6)
    msg = self._font_body.render(message, True, C_TEXT)
    screen.blit(msg, (x + (w - msg.get_width()) // 2, y + 16))
    for i, label in enumerate(["Yes", "No"]):
        col = C_HEADER if i == self._confirm_cursor else C_MUTED
        s = self._font_body.render(label, True, col)
        screen.blit(s, (x + 80 + i * 120, y + 60))
```

---

## Toast Notification (auto-dismiss)

```python
def __init__(self, ...):
    self._toast: str | None = None
    self._toast_timer: float = 0.0
    TOAST_DURATION = 1.8  # seconds

def _show_toast(self, message: str):
    self._toast       = message
    self._toast_timer = TOAST_DURATION

def update(self, delta: float):
    if self._toast_timer > 0:
        self._toast_timer -= delta
        if self._toast_timer <= 0:
            self._toast = None

def _draw_toast(self, screen):
    if not self._toast:
        return
    w, h = 400, 50
    x = (screen.get_width()  - w) // 2
    y = screen.get_height() - 80
    pygame.draw.rect(screen, (30, 30, 50), (x, y, w, h), border_radius=6)
    pygame.draw.rect(screen, (100, 220, 130), (x, y, w, h), 2, border_radius=6)
    msg = self._font_body.render(self._toast, True, (100, 220, 130))
    screen.blit(msg, (x + (w - msg.get_width()) // 2, y + (h - msg.get_height()) // 2))
```

---

## Multi-Page List (scrollable)

```python
def __init__(self, ...):
    self._items      = []   # full list
    self._page_size  = 8
    self._scroll_top = 0
    self._cursor     = 0

def _clamp_scroll(self):
    # keep cursor visible
    if self._cursor < self._scroll_top:
        self._scroll_top = self._cursor
    elif self._cursor >= self._scroll_top + self._page_size:
        self._scroll_top = self._cursor - self._page_size + 1

def handle_events(self, events):
    for event in events:
        if event.type != pygame.KEYDOWN:
            continue
        if event.key == pygame.K_UP:
            self._cursor = max(0, self._cursor - 1)
        elif event.key == pygame.K_DOWN:
            self._cursor = min(len(self._items) - 1, self._cursor + 1)
        self._clamp_scroll()

def _draw_list(self, screen, x, y, item_h=28):
    visible = self._items[self._scroll_top:self._scroll_top + self._page_size]
    for i, item in enumerate(visible):
        idx = self._scroll_top + i
        col = C_HEADER if idx == self._cursor else C_TEXT
        s = self._font_body.render(str(item), True, col)
        screen.blit(s, (x, y + i * item_h))
    # scroll indicator
    total = len(self._items)
    if total > self._page_size:
        hint = self._font_hint.render(
            f"{self._scroll_top + 1}–{min(self._scroll_top + self._page_size, total)} / {total}",
            True, C_MUTED)
        screen.blit(hint, (x, y + self._page_size * item_h + 4))
```
