# Frontend Design System (PM2-050)

## Theme Tokens

Defined in `src/theme/tokens.css`:

- Typography families (`--font-sans`, `--font-mono`)
- Color tokens for base, primary, success, warning, danger
- Radius, spacing, and shadow tokens

## Reusable UI Primitives

- `src/components/ui/Button.tsx`
- `src/components/ui/Card.tsx`
- `src/components/ui/TextInput.tsx`

These primitives are the default building blocks for PM2-051/052/053 screens.

## Layout Shell

- `src/components/layout/AppFrame.tsx`

Provides:

- App frame with left navigation
- Standard page header
- Shared session controls

## Global Notifications

- `src/components/notifications/ToastProvider.tsx`

Use from components/pages:

```tsx
const { notify } = useToast();
notify("Saved", "success");
notify("Could not save", "error");
```
