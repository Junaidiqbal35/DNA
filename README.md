# DNA TESTING SOLUTIONS — site update

Everything in this zip is either new or changed. Files you aren't given here
(cart, webstore, report templates, your forms, your settings) are untouched —
don't replace them.

---

## Why the site was rendering white

`base.html` loaded the Tailwind config like this:

```django
<script src="{% static 'tailwind-config.js' %}"></script>
```

The file is actually at `static/js/tailwind-config.js`. So the request 404'd,
the custom colours (`bg-paper`, `text-ink`, `bg-teal`, `border-line`) were
never registered with Tailwind, Tailwind emitted no CSS for them, and every
page came out white. The grid still worked, because those are built-in
classes — which is exactly why it looked like "design hi nahi aa rahi" rather
than a missing file.

Two things changed so this can't recur:

1. **The Tailwind config is now inline in `base.html`.** No file to miss, no
   `collectstatic` step to forget.
2. **`custom-styles.css` carries a colour fallback block.** If the Tailwind
   CDN is ever blocked or slow, the site degrades to plain-but-readable
   instead of white-on-white.

`base-functions.js` had the same wrong path and is fixed to `js/base-functions.js`.

Also found: `templates/pages/disclaimer.html` had been overwritten with the
*partial's* content, so `/disclaimer/` rendered a stray notice box with no
layout. The real page is restored. `pages/disclaimer.html` and
`partials/_disclaimer.html` are different files — keep them separate.

---

## Install

### 1. Templates and static

```
templates/base.html                    → replace
templates/pages/*.html                 → replace
templates/partials/*.html              → replace (_lab_strip.html is new)
static/css/custom-styles.css           → replace
static/js/tailwind-config.js           → keep (no longer loaded, harmless)
```

### 2. App code

```
core/models.py                         → replace (PartnerLab + LabCertification added)
core/views.py                          → replace (partners_view, about_view added)
core/admin_partners.py                 → new
core/urls_snippet.py                   → reference only, copy the routes you need
core/seed_data.json                    → new, edit this
core/management/commands/seed_dnalab.py → new
```

Register the admin — add this at the bottom of your existing `core/admin.py`:

```python
from .admin_partners import *  # noqa: F401,F403
```

### 3. Settings

Logos and certificates upload to MEDIA, so:

```python
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
```

and in the project `urls.py`, for local development:

```python
from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

Without this the uploads succeed but every image renders broken.

### 4. URLs

See `core/urls_snippet.py`. The new route is:

```python
path('partners/', views.partners_view, name='partners'),
```

The about page **must** go through `views.about_view` now — a bare
`TemplateView` won't pass the labs into the template, and the partner section
will silently fall back to the plain country list.

### 5. Migrate

```bash
python manage.py makemigrations core
python manage.py migrate
```

### 6. Seed

```bash
python manage.py seed_dnalab
```

---

## The seed command

```bash
python manage.py seed_dnalab                      # labs + certificates + products
python manage.py seed_dnalab --dry-run            # show what would happen, save nothing
python manage.py seed_dnalab --labs-only
python manage.py seed_dnalab --products-only
python manage.py seed_dnalab --placeholder-certs  # stand-in certificate images
python manage.py seed_dnalab --activate-labs      # seed labs switched on
python manage.py seed_dnalab --available-products # seed products switched on
python manage.py seed_dnalab --file other.json
```

It is idempotent — every record matches on `slug` via `update_or_create`, so
re-running after an edit updates instead of duplicating. Nothing is ever
deleted.

### Two deliberately cautious defaults

**Labs seed hidden (`is_active=False`).** Switch a lab live only once you hold
a current written agreement with it. A logo on your site is a partnership
claim, and it borrows that lab's accreditation.

**Products seed unavailable (`available=False`) with placeholder prices.** The
prices in `seed_data.json` are made up — put your real catalogue prices in
first, then flip them available. This is why the WhatsApp catalogue matters
(see below).

The command prints a checklist after every run telling you what still needs
real data.

### Images

Put real files here and the command picks them up by filename:

```
core/seed_assets/logos/alphabiolabs-logo.png
core/seed_assets/certificates/ukas-17025.jpg
```

Reference them in `seed_data.json` as `"logo": "alphabiolabs-logo.png"` and
`"image": "ukas-17025.jpg"`.

If a certificate has no image file, it is **skipped with a warning** rather
than created broken — a certificate with no document is not evidence of
anything. `--placeholder-certs` generates an obviously-fake stand-in marked
"PLACEHOLDER — NOT A REAL CERTIFICATE", so you can check the layout without
risking a fake reaching production.

---

## The catalogue

`seed_data.json` now holds your real catalogue, transcribed from the WhatsApp
screenshots: **30 products** with their actual names and prices. Where the
catalogue showed a struck-through price, that became `price` and the live
figure became `discounted_price`, matching how your model already works.

Two catalogue entries were deliberately **not** seeded as products:
*Appointment Scheduling* and *Services Disclaimer*. Neither is a thing anyone
buys — scheduling belongs in the booking flow and the disclaimer is a page.
Selling either as a catalogue line would put it in a shopping cart.

Transcribed from images, so check the figures against the app before going
live. The seed command reports exactly what still needs attention.

### Product grouping

Thirty tests in one flat grid is unusable, and it also sits a paternity swab
next to a 400-gene cancer panel, which are nothing alike to the person
reading. So `Product` gained two fields:

- **`category`** — relationship, immigration, prenatal, clinical, wellness,
  ancestry, other. The services page groups by this and gives each group a
  jump link.
- **`sample_type`** — swab, blood, maternal blood, tissue, other.

Current split: Clinical & hereditary 14, Immigration & legal 4, Wellness 4,
Other 3, Relationship 2, Prenatal 2, Ancestry 1.

### The thing worth acting on first

**15 of your 30 tests need a blood or tissue sample.** Your Pakistan office
collects buccal swabs — that is what the business model says, and it is what
the whole site now states. So more than half the catalogue cannot actually be
collected where the site implies it can.

Those tests are seeded with the right `sample_type`, and the services page
marks each one "Not collected at our Pakistan office — arranged through a
clinical collection partner", with a notice at the top of the list. That is
honest, but it is a stopgap. The real fix is to decide and document how blood
collection actually happens — a partner phlebotomy clinic, a hospital
arrangement, whatever it is — and then say so plainly.

### Claims to correct before these go live

**"USCIS Approved aaBB Accredited"** — reads as though USCIS has approved your
company. USCIS doesn't approve companies; it accepts reports from
AABB-accredited laboratories, and the accreditation belongs to the *lab*. The
product was reworded to "USA Immigration DNA Test (AABB accredited
laboratory)". Set its `lab` to whichever partner actually holds AABB.

**Three countries vs five.** The site says UK, US and Turkey. Your
catalogue images show otherwise: *NIFTY* is BGI's product (China / Hong Kong),
and the Fanconi Anemia panel image reads "powered by Mikrogen, Turkey". Either
add those labs and widen the wording everywhere — home page, about page,
disclaimer, footer — or confirm those tests route through a UK/US/AU lab. As
it stands the disclaimer is inaccurate, and the disclaimer is the one page
that cannot afford to be.

**Health-related results.** Clinical, prenatal and wellness tests now carry a
line saying results are produced and interpreted by the laboratory and should
be discussed with a qualified clinician, and that you cannot interpret them.
That is required by your own disclaimer, which says you give no genetic or
medical advice.

### Names

Your WhatsApp business is **DNA Testing Solutions (DTS®)**, the site says
**DNA TESTING SOLUTIONS**, the old About page said **DTS Lab  Pakistan**, and the
catalogue cards show **DNA Labs  Pakistan**. Four names for one business.

Worth settling — and "DNA TESTING SOLUTIONS" works against the disclaimer sitting
right beside it, since the name itself implies a lab in  Pakistan. "DNA Testing
Solutions" doesn't have that problem.

One good thing: your catalogue's own Services Disclaimer card states the same
scope the website now states — not a testing laboratory, no on-site testing,
no medical/legal/genetic advice, sample coordination only. The two agree,
which is what you want if anyone ever compares them.

---

## Labs seeded, and two left out

Seeded from your old About page and the logos visible in your catalogue
images, all hidden until you verify them: AlphaBiolabs (GB), DNA-Q (AU),
Endeavor DNA Laboratories (US), Eurofins (GB), Dynamic DNA Laboratories (US),
Universal Forensics (US).

**Country values are guesses — check each one.** Eurofins in particular
operates in many countries; set it to the specific site your samples actually
reach.

**Cenata and BGI were left out.** They were on your old About page, but Cenata
is German and BGI is Chinese, and the whole site states three countries —
UK, US, Turkey. If you genuinely ship to them, add them back to
`seed_data.json` and update the disclaimer wording, because it currently names
three countries and would be wrong.

---

## Two things in views.py that were changed on purpose

Both were in `addon_options` and both cut across the business model:

**"Express Processing (12-24 hours)"** — not deliverable. The sample has to
clear a Pakistan-to-overseas courier leg before testing starts, so 12–24 hours
can't be sold. Replaced with "Priority courier to the laboratory", which
shortens transit and says so, rather than promising a total turnaround.

**"Genetic Counseling Session"** — the Pakistan office provides no genetic or
medical interpretation, so selling counselling from there contradicts the
disclaimer directly. Removed. If a partner lab offers it, sell it as that
lab's service and name the lab.

---

## If something still doesn't run

- **`NoReverseMatch: 'partners'`** — add the partners route. `PartnerLab.get_absolute_url`
  already falls back to a plain path, so this should only come from a template
  using `{% url 'partners' %}`.
- **Logos and certificates upload but show broken** — MEDIA_URL / MEDIA_ROOT
  and the dev `static()` line are missing. See step 3.
- **Still white after replacing base.html** — hard-refresh (Ctrl+Shift+R); the
  old HTML caches aggressively. Then check the browser Network tab for a 404
  on `custom-styles.css`.
- **Partner section shows only "United Kingdom / United States / Turkey"**
  — the view isn't passing `partner_labs`. On the about page that means it's
  still a `TemplateView`.
- **Images under `static/images/` 404** — that folder doesn't exist in the
  static tree you sent. That's why the old hardcoded partner logos were
  broken, and why labs are database-driven now. Upload logos through the
  admin instead of adding them back to static.
