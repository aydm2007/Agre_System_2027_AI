# 🎨 AgriAsset 2025 Premium Design System

## Color Palette

### Dark Theme (Primary)
```css
--bg-primary: #0a0f0d;      /* Dark green-black */
--surface-1: rgba(255,255,255,0.05);
--surface-2: rgba(255,255,255,0.10);
--border: rgba(255,255,255,0.10);
--text-primary: #ffffff;
--text-secondary: rgba(255,255,255,0.50);
```

### Accent Colors
```css
--emerald: #10b981;         /* Primary action */
--amber: #f59e0b;           /* Warning/highlight */
--rose: #f43f5e;            /* Danger/negative */
--purple: #a855f7;          /* Special action */
```

## Components

### GlassCard
```jsx
className="rounded-3xl border border-white/10 
  bg-gradient-to-br from-white/5 to-white/[0.02] 
  backdrop-blur-xl shadow-2xl"
```

### PremiumButton
```jsx
// Primary
className="px-4 py-2.5 rounded-xl bg-emerald-600 
  text-white font-bold shadow-lg shadow-emerald-500/20 
  hover:bg-emerald-500 transition-all"

// Secondary
className="px-4 py-2.5 rounded-xl bg-white/5 
  border border-white/10 text-white/70 
  hover:bg-white/10 transition-all"
```

### Gradient Text
```jsx
className="bg-gradient-to-r from-emerald-400 to-amber-200 
  bg-clip-text text-transparent"
```

## Typography
- **Headers**: font-black tracking-tight
- **Labels**: text-[10px] uppercase font-bold tracking-wider
- **Body**: text-sm font-medium

## Animations
- **Hover Scale**: hover:scale-[1.02]
- **Hover Lift**: hover:-translate-y-1
- **Transitions**: transition-all duration-300

## RTL Support
```jsx
<div dir="rtl" className="...">
```
