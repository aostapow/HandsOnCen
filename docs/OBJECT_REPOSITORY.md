# Object Repository (UFT-style)

Logical object names are stored per application under `~/.handson/repositories/`.

## Naming

Use hierarchical paths: `windowKey/objectName` — e.g. `frmMain/btnGuardar`.

## Auto-capture

After successful `smart_find`, `click_element`, or `repo_find` with `remember=true` (default):

- Identification props (mandatory + assistive)
- Full snapshot via `capture_object_snapshot` (images + phash)
- Strategy memory update

## Image assets

| File | Use |
|------|-----|
| `*_crop.png` | Exact element bbox |
| `*_context.png` | Bbox + 20% padding |
| `*_template.png` | OpenCV template matching fallback |
| `*_annotated.png` | Window with red highlight |

## Tools

- `repo_find(repo_path)` — resolve logical name
- `repo_list()` — list stored objects
- `highlight_element(repo_path=...)` — mark object on screen
