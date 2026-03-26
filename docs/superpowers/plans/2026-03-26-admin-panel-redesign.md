# Admin Panel Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the admin panel with a light modern theme — white sidebar, gradient accents, improved dashboard with charts, styled tables with avatars/badges, and a 3-chart analytics page.

**Architecture:** Pure template/CSS rewrite + minor route changes. All 8 admin templates get rewritten. `api/index.py` gets updated routes to pass additional data (recent screenings with baby names, screening/notification stats, avatar colors). No new dependencies — Bootstrap 5, Chart.js, Inter font via CDN.

**Tech Stack:** Jinja2 templates, Bootstrap 5.3.3, Chart.js 4.4.7, Inter font (Google Fonts), inline CSS

**Spec:** `docs/superpowers/specs/2026-03-26-admin-panel-redesign.md`

---

### Task 1: Update api/index.py — add new template data

**Files:**
- Modify: `api/index.py` (admin routes, lines 502-573)

This task adds all new server-side data that templates will need. No template changes yet — just data.

- [ ] **Step 1: Add avatar color palette and helper**

Add after the `_get_admin` function (around line 448):

```python
AVATAR_COLORS = [
    "#dbeafe", "#dcfce7", "#fef3c7", "#fce7f3",
    "#e0e7ff", "#ccfbf1", "#fee2e2", "#f3e8ff",
]

def _avatar_color(name: str) -> str:
    return AVATAR_COLORS[hash(name) % len(AVATAR_COLORS)]
```

- [ ] **Step 2: Update admin_dashboard route**

Replace the `admin_dashboard` function body to add `recent_screenings` and `region_stats`:

```python
@app.get("/admin/", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    user = _get_admin(request)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=302)

    # Build baby name lookup
    baby_names = {b.id: b.name for b in DB["babies"]}

    # Recent screenings with baby name
    sorted_screenings = sorted(DB["screenings"], key=lambda s: s.received_at or s.created_at, reverse=True)
    recent_screenings = [{
        "baby_name": baby_names.get(s.baby_id, "—"),
        "disease_name": s.disease_name or "—",
        "result_type": s.result_type.value,
        "received_at": s.received_at.strftime("%d.%m.%Y") if s.received_at else "—",
    } for s in sorted_screenings[:5]]

    # Region stats
    region_counter = Counter(p.region for p in DB["parents"] if p.region)
    region_stats = [{"region": r, "count": c} for r, c in region_counter.most_common()]

    return _render(admin_tpl, request, "dashboard.html", {
        "user": user,
        "total_parents": len(DB["parents"]),
        "total_babies": len(DB["babies"]),
        "total_screenings": len(DB["screenings"]),
        "positive_count": sum(1 for s in DB["screenings"] if s.result_type == ResultType.positive),
        "pending_notifs": sum(1 for n in DB["notifications"] if n.status in (NotificationStatus.pending, NotificationStatus.sent)),
        "confirmed_notifs": sum(1 for n in DB["notifications"] if n.status == NotificationStatus.confirmed),
        "recent_screenings": recent_screenings,
        "region_stats": region_stats,
    })
```

- [ ] **Step 3: Update admin_parents route — add avatar colors and initials**

```python
@app.get("/admin/parents", response_class=HTMLResponse)
async def admin_parents(request: Request):
    user = _get_admin(request)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=302)

    parents = [{
        "id": str(p.id),
        "full_name": p.full_name,
        "initials": "".join(w[0] for w in p.full_name.split()[:2]) if p.full_name else "?",
        "avatar_color": _avatar_color(p.full_name or ""),
        "phone": p.phone,
        "region": p.region,
        "registration_date": p.registration_date.strftime("%d.%m.%Y") if p.registration_date else "—",
        "babies_count": len(p.babies),
    } for p in DB["parents"]]

    return _render(admin_tpl, request, "parents.html", {"user": user, "parents": parents})
```

- [ ] **Step 4: Update admin_screening route — add baby names**

```python
@app.get("/admin/screening", response_class=HTMLResponse)
async def admin_screening(request: Request):
    user = _get_admin(request)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=302)

    baby_names = {b.id: b.name for b in DB["babies"]}
    results = [{
        "baby_name": baby_names.get(s.baby_id, "—"),
        "result_type": s.result_type,
        "disease_code": s.disease_code,
        "disease_name": s.disease_name,
        "received_at": s.received_at,
        "source": s.source,
    } for s in sorted(DB["screenings"], key=lambda s: s.received_at or s.created_at, reverse=True)]

    return _render(admin_tpl, request, "screening.html", {"user": user, "results": results})
```

- [ ] **Step 5: Update admin_notifications route — add parent names**

```python
@app.get("/admin/notifications", response_class=HTMLResponse)
async def admin_notifications(request: Request):
    user = _get_admin(request)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=302)

    parent_names = {p.id: p.full_name for p in DB["parents"]}
    notifications = [{
        "parent_name": parent_names.get(n.parent_id, "—"),
        "status": n.status,
        "message_text": n.message_text,
        "retry_count": n.retry_count,
        "sent_at": n.sent_at,
        "confirmed_at": n.confirmed_at,
        "created_at": n.created_at,
    } for n in sorted(DB["notifications"], key=lambda n: n.created_at, reverse=True)]

    return _render(admin_tpl, request, "notifications.html", {"user": user, "notifications": notifications})
```

- [ ] **Step 6: Update admin_analytics route — add screening and notification stats**

```python
@app.get("/admin/analytics", response_class=HTMLResponse)
async def admin_analytics(request: Request):
    user = _get_admin(request)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=302)

    region_counter = Counter(p.region for p in DB["parents"] if p.region)
    region_stats = [{"region": r, "count": c} for r, c in region_counter.most_common()]

    screening_stats = {
        "negative": sum(1 for s in DB["screenings"] if s.result_type == ResultType.negative),
        "positive": sum(1 for s in DB["screenings"] if s.result_type == ResultType.positive),
        "repeat": sum(1 for s in DB["screenings"] if s.result_type == ResultType.repeat_needed),
    }

    notification_stats = {
        "confirmed": sum(1 for n in DB["notifications"] if n.status == NotificationStatus.confirmed),
        "sent": sum(1 for n in DB["notifications"] if n.status == NotificationStatus.sent),
        "pending": sum(1 for n in DB["notifications"] if n.status == NotificationStatus.pending),
        "escalated": sum(1 for n in DB["notifications"] if n.status == NotificationStatus.escalated),
    }

    return _render(admin_tpl, request, "analytics.html", {
        "user": user,
        "region_stats": region_stats,
        "screening_stats": screening_stats,
        "notification_stats": notification_stats,
    })
```

- [ ] **Step 7: Test locally**

Run: `python3 -m uvicorn api.index:app --host 127.0.0.1 --port 8005`
Test: `curl -s -o /dev/null -w "%{http_code}" -c /tmp/t -b /tmp/t http://127.0.0.1:8005/demo/admin && curl -s -o /dev/null -w "%{http_code}" -b /tmp/t http://127.0.0.1:8005/admin/`
Expected: `302` then `200`

- [ ] **Step 8: Commit**

```bash
git add api/index.py
git commit -m "feat(admin): add avatar colors, recent screenings, screening/notification stats to routes"
```

---

### Task 2: Rewrite base.html — new sidebar and global styles

**Files:**
- Rewrite: `src/admin/templates/base.html`

Complete rewrite of the layout: white sidebar, Inter font, new color system, all CSS for child templates.

- [ ] **Step 1: Write new base.html**

Full file content — see spec sections 1 (General Style) and 2 (Sidebar). Key elements:
- Inter font from Google Fonts
- White sidebar (260px) with border-right
- Gradient logo text
- Nav items with icon circles and active_page highlighting
- Avatar circle + Администратор at bottom
- All shared CSS: `.admin-card`, `.admin-table`, stat cards, badges, etc.
- `{% block content %}`, `{% block extra_head %}`, `{% block extra_scripts %}`

- [ ] **Step 2: Test — verify sidebar renders**

Run local server, visit `/demo/admin`, verify sidebar appears with new white style.

- [ ] **Step 3: Commit**

```bash
git add src/admin/templates/base.html
git commit -m "feat(admin): rewrite base.html with white sidebar, Inter font, modern CSS"
```

---

### Task 3: Rewrite dashboard.html

**Files:**
- Rewrite: `src/admin/templates/dashboard.html`

New dashboard with 3 stat cards (top), 3 compact status cards (middle), recent results list (bottom-left), CSS region bars (bottom-right).

- [ ] **Step 1: Write new dashboard.html**

Key elements from spec section 3:
- Top row: 3 cards with large number, label, icon circle, hardcoded trend (↑ 12%, ↑ 8%, ↑ 15%)
- Middle row: 3 compact cards with colored left border
- Bottom left (col-md-7): "Последние результаты" — loop over `recent_screenings`, show baby_name, disease_name, result badge, date
- Bottom right (col-md-5): "По районам" — CSS bars using `region_stats`, bar width as percentage of max

- [ ] **Step 2: Test — verify dashboard renders with all data**

Visit `/demo/admin`, verify all 6 stat cards show correct numbers, recent results list shows 5 items, region bars display.

- [ ] **Step 3: Commit**

```bash
git add src/admin/templates/dashboard.html
git commit -m "feat(admin): new dashboard with stat cards, recent results, region bars"
```

---

### Task 4: Rewrite parents.html

**Files:**
- Rewrite: `src/admin/templates/parents.html`

- [ ] **Step 1: Write new parents.html**

Key elements from spec section 4 (Parents):
- Card wrapper with header (title + badge + search input)
- Table with styled headers (uppercase, small, gray)
- Each row: avatar circle (initials + color from `avatar_color`), full_name, phone (monospace), region (colored pill), date, babies count badge
- Zebra striping, hover highlight

- [ ] **Step 2: Test — verify table renders**

Visit `/admin/parents`, verify avatars show initials with colors, region pills display.

- [ ] **Step 3: Commit**

```bash
git add src/admin/templates/parents.html
git commit -m "feat(admin): styled parents table with avatar initials and region pills"
```

---

### Task 5: Rewrite babies.html

**Files:**
- Rewrite: `src/admin/templates/babies.html`

- [ ] **Step 1: Write new babies.html**

Key elements from spec section 4 (Babies):
- Same card/table wrapper style as parents
- Gender icon: check if name ends with а/я → female (bi-gender-female, pink), else male (bi-gender-male, blue)
- Sample collected: green check icon + "Выполнен" or red X icon + "Нет"

- [ ] **Step 2: Test — verify gender icons and status indicators**

Visit `/admin/babies`, verify icons show correctly.

- [ ] **Step 3: Commit**

```bash
git add src/admin/templates/babies.html
git commit -m "feat(admin): styled babies table with gender icons and status indicators"
```

---

### Task 6: Rewrite screening.html

**Files:**
- Rewrite: `src/admin/templates/screening.html`

- [ ] **Step 1: Write new screening.html**

Key elements from spec section 4 (Screening):
- Baby name column (new)
- Result badges with icons: bi-check-circle (green/negative), bi-exclamation-triangle (red/positive), bi-arrow-repeat (orange/repeat)
- Disease code in gray pill
- Disease name bold

- [ ] **Step 2: Test — verify all columns render**

Visit `/admin/screening`, verify baby names appear, badges have icons.

- [ ] **Step 3: Commit**

```bash
git add src/admin/templates/screening.html
git commit -m "feat(admin): styled screening table with baby names and icon badges"
```

---

### Task 7: Rewrite notifications.html

**Files:**
- Rewrite: `src/admin/templates/notifications.html`

- [ ] **Step 1: Write new notifications.html**

Key elements from spec section 4 (Notifications):
- Parent name column (new)
- Colored left border per row (4px) based on status
- Status badge colors from spec
- Full message text, 0.85rem font
- `delivered` status handled same as `sent`

- [ ] **Step 2: Test — verify colored borders and parent names**

Visit `/admin/notifications`, verify borders match status colors.

- [ ] **Step 3: Commit**

```bash
git add src/admin/templates/notifications.html
git commit -m "feat(admin): styled notifications table with colored borders and parent names"
```

---

### Task 8: Rewrite analytics.html

**Files:**
- Rewrite: `src/admin/templates/analytics.html`

- [ ] **Step 1: Write new analytics.html**

Key elements from spec section 5:
- Block 1 (full width): horizontal bar chart (Chart.js, indexAxis: 'y'), gradient bars, region data
- Block 2 (col-md-6): doughnut chart for screening results (3 segments: neg/pos/repeat)
- Block 3 (col-md-6): doughnut chart for notification statuses (4 segments)
- Chart.js loaded in `{% block extra_head %}`
- All chart config in `{% block extra_scripts %}`
- Custom legends next to doughnut charts with counts

- [ ] **Step 2: Test — verify all 3 charts render**

Visit `/admin/analytics`, verify horizontal bar chart + 2 doughnut charts display.

- [ ] **Step 3: Commit**

```bash
git add src/admin/templates/analytics.html
git commit -m "feat(admin): analytics page with 3 Chart.js charts (bars + 2 donuts)"
```

---

### Task 9: Update login.html — add Inter font

**Files:**
- Modify: `src/admin/templates/login.html`

- [ ] **Step 1: Add Inter font link**

Add after the Bootstrap CSS link:
```html
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
```

Add to `<style>`:
```css
* { font-family: 'Inter', sans-serif; }
```

- [ ] **Step 2: Commit**

```bash
git add src/admin/templates/login.html
git commit -m "feat(admin): add Inter font to login page"
```

---

### Task 10: Full integration test and push

- [ ] **Step 1: Start local server**

```bash
python3 -m uvicorn api.index:app --host 127.0.0.1 --port 8005
```

- [ ] **Step 2: Test all admin pages return 200**

```bash
curl -s -c /tmp/ft http://127.0.0.1:8005/demo/admin -o /dev/null -w "%{http_code}"
for path in /admin/ /admin/parents /admin/babies /admin/screening /admin/notifications /admin/analytics; do
  curl -s -b /tmp/ft "http://127.0.0.1:8005$path" -o /dev/null -w "%{http_code} $path\n"
done
```

Expected: all `200`

- [ ] **Step 3: Visual check via browser**

Open `http://localhost:8005/demo/admin` in browser. Verify:
- White sidebar with gradient logo
- Dashboard stat cards with trends
- Recent results list
- Region bars
- All table pages render correctly
- Analytics charts display

- [ ] **Step 4: Push to GitHub**

```bash
git push
```

Vercel will auto-deploy. Verify at https://genetiki.vercel.app/demo/admin
