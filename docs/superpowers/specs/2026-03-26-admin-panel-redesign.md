# Admin Panel Redesign — Design Spec

## Context

Demo admin panel for neonatal screening project (project defense). FastAPI + Jinja2 + Bootstrap 5, deployed on Vercel with in-memory mock data. Current panel has a dark navy sidebar, plain Bootstrap tables, and basic stat cards.

## Design Direction

Light modern theme with Inter font, soft shadows, rounded cards, gradient accents (blue-to-green). Consistent with the dark landing page by sharing the same font and accent colors but using a light palette appropriate for a data-heavy admin interface.

## 1. General Style

- **Body**: #f8f9fa background
- **Font**: Inter (Google Fonts, already loaded on landing)
- **Cards**: white background, border-radius: 16px, box-shadow: 0 1px 3px rgba(0,0,0,.06)
- **Accent gradient**: linear-gradient(135deg, #3b82f6, #10b981) for key elements
- **Hover animations**: translateY(-2px) + shadow increase on cards, soft highlight on table rows
- **Color palette**: primary #3b82f6, success #10b981, warning #f59e0b, danger #ef4444

## 2. Sidebar

- **Background**: white, border-right: 1px solid #e5e7eb
- **Width**: 260px
- **Logo**: "НС Якутия" with heart-pulse icon, gradient text
- **Nav items**: gray text (#6b7280), icon on colored circle bg (40px), text beside it
- **Active item**: blue text (#3b82f6), 3px left border accent, light blue bg (rgba(59,130,246,.06))
- **Hover**: same light blue bg
- **Bottom section**: avatar circle with initials "А" + "Администратор" label + logout link
- **No collapse behavior** — fixed sidebar, always visible (desktop-only demo)

## 3. Dashboard

### Top row — 3 stat cards

| Card | Value | Icon | Accent |
|------|-------|------|--------|
| Родители | total_parents | bi-people | blue circle bg |
| Дети | total_babies | bi-person-hearts | green circle bg |
| Скрининг | total_screenings | bi-clipboard2-pulse | amber circle bg |

Each card:
- Large number (2rem, font-weight 700)
- Small gray label below
- Icon on colored circle (48px) aligned right
- Fake trend indicator below number: "↑ 12% за месяц" in green small text (hardcoded)

### Middle row — 3 status cards (compact)

| Card | Value | Color |
|------|-------|-------|
| Положительных | positive_count | red accent left border |
| Ожидающих | pending_notifs | orange accent left border |
| Подтверждённых | confirmed_notifs | green accent left border |

Compact: number + label on one line, colored left border (4px), no icon circles.

### Bottom row — 2 blocks

**Left (col-md-7): "Последние результаты"**
- Card with list of 5 most recent screening results
- Each item: baby name, disease name, result badge, date
- Compact list (no table), items separated by thin border-bottom
- Result badges: green pill (отрицательный), red pill (положительный), orange pill (повторный)

**Right (col-md-5): "По районам"**
- CSS horizontal bar chart (no Chart.js needed here)
- Each region: label left, bar in middle (gradient fill), count right
- Bars proportional to max value
- Max 6-8 items shown

## 4. Tables (Parents, Babies, Screening, Notifications)

### Common table style
- Wrapped in white card (border-radius: 16px)
- Card header: page title (h5) + pill badge with count + search input (visual only, no JS)
- No visible cell borders — separation via alternating row bg (#fafbfc on even rows)
- Row hover: bg #f0f4ff
- Rounded status badges throughout
- th: uppercase, small (0.7rem), letter-spacing .05em, color #9ca3af, no border-bottom — just padding

### Parents table specifics
- Avatar circle (36px) with initials, colored bg (derived from name hash) — before full_name
- Region shown as colored chip/pill (light bg + colored text)
- Phone in monospace font

### Babies table specifics
- Gender icon before name: bi-gender-male (blue) / bi-gender-female (pink), determined by name ending (Russian names: -а/-я = female, else male)
- Sample collected: bi-check-circle-fill green icon + "Выполнен" / bi-x-circle red icon + "Нет" instead of "Да/Нет" badges

### Screening table specifics
- Result badges larger with icons: bi-check-circle (negative/green), bi-exclamation-triangle (positive/red), bi-arrow-repeat (repeat/orange)
- Disease code in a gray pill badge
- Disease name is the primary text (bolder)

### Notifications table specifics
- Colored left border on each row (4px), color matches status
- Status badge colors: confirmed=#10b981, sent=#3b82f6, pending=#9ca3af, escalated=#ef4444
- Message text shown fully (no truncation), smaller font size (0.85rem)

## 5. Analytics Page

### Block 1 (full width): "Распределение по районам"
- Horizontal bar chart (Chart.js)
- Gradient bars (blue→green)
- Labels on Y-axis (region names), values at bar ends
- indexAxis: 'y', no grid lines on Y, subtle grid on X

### Block 2 (col-md-6): "Результаты скрининга"
- Doughnut chart (Chart.js)
- 3 segments: negative (green #10b981), positive (red #ef4444), repeat_needed (orange #f59e0b)
- Legend to the right of chart with counts
- Data: count each result_type from DB["screenings"]

### Block 3 (col-md-6): "Статус уведомлений"
- Doughnut chart (Chart.js)
- 4 segments: confirmed (green), sent (blue), pending (gray), escalated (red)
- Legend to the right with counts
- Data: count each status from DB["notifications"]

## 6. Data Changes in api/index.py

New template variables needed:

**Dashboard:**
- `recent_screenings`: last 5 screening results with baby name attached
- `region_stats`: list of {region, count} (already exists for analytics, reuse)

**Analytics:**
- `screening_stats`: {negative: N, positive: N, repeat: N}
- `notification_stats`: {confirmed: N, sent: N, pending: N, escalated: N}

## 7. Files to Change

| File | Action |
|------|--------|
| `src/admin/templates/base.html` | Rewrite — new sidebar, Inter font, new styles |
| `src/admin/templates/dashboard.html` | Rewrite — new stat cards, recent results, region bars |
| `src/admin/templates/parents.html` | Rewrite — avatar initials, chips, new table style |
| `src/admin/templates/babies.html` | Rewrite — gender icons, new status indicators |
| `src/admin/templates/screening.html` | Rewrite — larger badges with icons, pill codes |
| `src/admin/templates/notifications.html` | Rewrite — colored borders, full text |
| `src/admin/templates/analytics.html` | Rewrite — 3 chart blocks |
| `src/admin/templates/login.html` | Minor — match new font/style |
| `api/index.py` | Update — add recent_screenings, screening_stats, notification_stats |

## 8. Out of Scope

- No JavaScript interactivity (search, sort, filter) — visual only for demo
- No responsive/mobile layout — desktop-only for projection at defense
- No dark mode toggle
- Login page stays minimal (just font update)
