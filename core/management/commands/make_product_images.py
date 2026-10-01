"""Render a consistent product tile for every test in the catalogue.

    python manage.py make_product_images                 # write PNGs to media/product_tiles/
    python manage.py make_product_images --attach        # also set Product.image
    python manage.py make_product_images --slug paternity-test
    python manage.py make_product_images --size 1080 --contact-sheet

Why a generator rather than one-off artwork: thirty tests today and more
later. A command means the thirty-first tile matches the first thirty without
anyone having to remember the margins, and a palette change is one edit.

The look is a laboratory specimen plate — a white card on a paper field with a
real soft shadow, carrying a fine-line technical diagram chosen by category.
Deliberately not a glowing helix on a dark gradient: that is the stock image
every DNA site uses, and it reads as decoration rather than as this product.
"""

import hashlib
import math
import subprocess
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError

from core.models import Product

# --------------------------------------------------------------------------
# Design tokens — the same palette the website uses
# --------------------------------------------------------------------------

PAPER = (244, 248, 246)
PLATE = (255, 255, 255)
INK = (11, 64, 61)
TEAL = (14, 110, 102)
TEAL_SOFT = (26, 138, 127)
LINE = (217, 232, 227)
AMBER = (194, 124, 16)

SS = 3  # supersampling factor; lines are drawn at 3x then downsampled


# Serif faces to look for, best first. Metric-compatible clones come before
# the Microsoft originals so Linux and Windows land on a similar shape.
SERIF_CANDIDATES = [
    'Caladea-Regular.ttf',      # Linux (crosextra) — Cambria-compatible
    'cambria.ttc', 'Cambria.ttc',
    'georgia.ttf', 'Georgia.ttf',
    'constan.ttf',              # Constantia
    'Charter.ttc', 'CharterBT-Roman.otf',
    'LiberationSerif-Regular.ttf',
    'DejaVuSerif.ttf',
    'NotoSerif-Regular.ttf',
    'Times New Roman.ttf', 'times.ttf', 'Times.ttc',
    'FreeSerif.ttf',
]

# Where fonts live on each OS. Checked in order, recursively.
FONT_DIRS = [
    Path('C:/Windows/Fonts'),                               # Windows
    Path.home() / 'AppData/Local/Microsoft/Windows/Fonts',  # Windows, per-user
    Path('/System/Library/Fonts'),                          # macOS
    Path('/System/Library/Fonts/Supplemental'),
    Path('/Library/Fonts'),
    Path.home() / 'Library/Fonts',
    Path('/usr/share/fonts'),                               # Linux
    Path('/usr/local/share/fonts'),
    Path.home() / '.local/share/fonts',
    Path.home() / '.fonts',
]


def find_serif_font(explicit=None):
    """Locate a usable serif TTF/OTF on any platform.

    The first version of this shelled out to `fc-match`, which exists on Linux
    and macOS but not on Windows — so the command died with 'No serif font
    found' before drawing anything. Now: an explicit path wins, then a scan of
    the normal font directories for known faces, then fontconfig if present,
    then whatever matplotlib ships. Pass --font to override any of it.
    """
    if explicit:
        path = Path(explicit).expanduser()
        if not path.exists():
            raise CommandError(f'--font path does not exist: {path}')
        return str(path)

    # 1. Known faces in the standard font directories.
    for directory in FONT_DIRS:
        try:
            if not directory.is_dir():
                continue
        except OSError:
            continue
        index = {}
        try:
            for item in directory.rglob('*'):
                if item.suffix.lower() in ('.ttf', '.otf', '.ttc'):
                    index.setdefault(item.name.lower(), item)
        except OSError:
            continue
        for candidate in SERIF_CANDIDATES:
            hit = index.get(candidate.lower())
            if hit:
                return str(hit)

    # 2. fontconfig, where it exists.
    for family in ('Caladea', 'Georgia', 'Liberation Serif', 'DejaVu Serif', 'serif'):
        try:
            out = subprocess.run(['fc-match', '-f', '%{file}', family],
                                 capture_output=True, text=True, timeout=10).stdout.strip()
            if out and Path(out).suffix.lower() in ('.ttf', '.otf', '.ttc'):
                return out
        except Exception:
            break

    # 3. matplotlib bundles DejaVu, and is often already installed.
    try:
        import matplotlib
        bundled = Path(matplotlib.__file__).parent / 'mpl-data' / 'fonts' / 'ttf' / 'DejaVuSerif.ttf'
        if bundled.exists():
            return str(bundled)
    except Exception:
        pass

    raise CommandError(
        'No serif font found.\n'
        'Point the command at one directly, for example:\n'
        '  Windows:  python manage.py make_product_images --font C:/Windows/Fonts/georgia.ttf\n'
        '  macOS:    python manage.py make_product_images --font /Library/Fonts/Georgia.ttf\n'
        '  Linux:    sudo apt install fonts-crosextra-caladea\n'
    )


class Command(BaseCommand):
    help = 'Render a square catalogue tile for each product.'

    def add_arguments(self, parser):
        parser.add_argument('--size', type=int, default=1080)
        parser.add_argument('--slug', help='Render one product only.')
        parser.add_argument('--out', default='',
                            help='Folder under MEDIA_ROOT. Default product_tiles.')
        parser.add_argument('--attach', action='store_true',
                            help='Also set Product.image to the rendered tile.')
        parser.add_argument('--overwrite', action='store_true',
                            help='With --attach, replace an image that already exists.')
        parser.add_argument('--contact-sheet', action='store_true',
                            help='Also write a grid of every tile for review.')
        parser.add_argument('--no-label', action='store_true',
                            help='Draw the motif only, without the product name. '
                                 'Use this set on the site, where the card already '
                                 'shows the name as real text — baking it into the '
                                 'image as well duplicates it, crops badly in a '
                                 'card, and is invisible to search. Keep the '
                                 'labelled set for WhatsApp, ads and print.')
        parser.add_argument('--font',
                            help='Path to a .ttf/.otf serif font, if the '
                                 'automatic search does not find one.')

    # ---------------------------------------------------------------- #

    def handle(self, *args, **options):
        try:
            from PIL import Image, ImageDraw, ImageFilter, ImageFont
        except ImportError:
            raise CommandError('Pillow is required: pip install Pillow')

        self.Image, self.ImageDraw = Image, ImageDraw
        self.ImageFilter, self.ImageFont = ImageFilter, ImageFont

        self.serif_path = find_serif_font(options.get('font'))
        # Fail here with a clear message rather than part-way through the
        # catalogue. .ttc collections open at index 0, which is the regular cut.
        try:
            self.ImageFont.truetype(self.serif_path, 40)
        except Exception as exc:
            raise CommandError(
                f'Found a font but Pillow could not open it:\n  {self.serif_path}\n'
                f'  {exc}\n'
                'Pass a different one with --font, e.g. '
                '--font C:/Windows/Fonts/georgia.ttf'
            )
        self.stdout.write(f'  font: {self.serif_path}\n')

        from django.conf import settings
        out_dir = Path(settings.MEDIA_ROOT) / (
            options['out'] or ('product_tiles_plain' if options['no_label']
                               else 'product_tiles'))
        out_dir.mkdir(parents=True, exist_ok=True)

        products = Product.objects.all().order_by('category', 'name')
        if options['slug']:
            products = products.filter(slug=options['slug'])
            if not products:
                raise CommandError(f"No product with slug {options['slug']}")

        size = options['size']
        written = []

        for product in products:
            image = self.render_tile(product, size, label=not options['no_label'])
            path = out_dir / f'{product.slug}.png'
            image.save(path, 'PNG', optimize=True)
            written.append((product, path, image))

            if options['attach'] and (options['overwrite'] or not product.image):
                with path.open('rb') as fh:
                    product.image.save(f'{product.slug}.png',
                                       ContentFile(fh.read()), save=True)

            self.stdout.write(f'  {product.slug}.png  —  {product.name}')

        if options['contact_sheet'] and written:
            sheet = self.contact_sheet([i for _, _, i in written])
            sheet_path = out_dir / '_contact-sheet.png'
            sheet.save(sheet_path, 'PNG', optimize=True)
            self.stdout.write(f'\n  contact sheet: {sheet_path}')

        self.stdout.write(self.style.SUCCESS(
            f'\n{len(written)} tile(s) written to {out_dir}'))

    # ---------------------------------------------------------------- #
    # Composition
    # ---------------------------------------------------------------- #

    def render_tile(self, product, size, label=True):
        Image, ImageDraw, ImageFilter = self.Image, self.ImageDraw, self.ImageFilter
        S = size * SS

        canvas = Image.new('RGB', (S, S), PAPER)

        # A faint top-down light falloff. Subtle enough to read as lighting
        # rather than as a gradient someone chose.
        light = Image.new('L', (1, S))
        for y in range(S):
            t = y / S
            light.putpixel((0, y), int(255 - 26 * (t ** 1.4)))
        light = light.resize((S, S))
        canvas = Image.composite(
            canvas, Image.new('RGB', (S, S), (231, 240, 236)), light)

        margin = int(S * 0.075)
        plate = (margin, margin, S - margin, S - margin)
        radius = int(S * 0.022)

        # Real soft shadow: a blurred black plate offset downward.
        shadow = Image.new('L', (S, S), 0)
        ImageDraw.Draw(shadow).rounded_rectangle(
            (plate[0] + int(S * 0.006), plate[1] + int(S * 0.016),
             plate[2] + int(S * 0.006), plate[3] + int(S * 0.016)),
            radius=radius, fill=70)
        shadow = shadow.filter(ImageFilter.GaussianBlur(int(S * 0.018)))
        canvas.paste(Image.new('RGB', (S, S), (118, 145, 139)), (0, 0), shadow)

        draw = ImageDraw.Draw(canvas)
        draw.rounded_rectangle(plate, radius=radius, fill=PLATE,
                               outline=LINE, width=max(1, int(S * 0.0012)))

        inset = int(S * 0.075)
        box = (plate[0] + inset, plate[1] + inset,
               plate[2] - inset, plate[3] - inset)

        if label:
            # Diagram in the upper area; type sits beneath a hairline.
            art_bottom = box[1] + int((box[3] - box[1]) * 0.64)
            self.draw_motif(draw, product, (box[0], box[1], box[2], art_bottom))

            rule_y = art_bottom + int(S * 0.045)
            draw.line((box[0], rule_y, box[2], rule_y),
                      fill=LINE, width=max(1, int(S * 0.0012)))
            self.draw_name(draw, product.name, box, rule_y + int(S * 0.045), S)
        else:
            # No type: let the diagram have the whole plate, centred.
            self.draw_motif(draw, product, box)

        return canvas.resize((size, size), self.Image.LANCZOS)

    def draw_name(self, draw, name, box, top, S):
        """Set the product name, wrapped, never truncated.

        The names run from 'BioAge Test' to 'Oncomine Comprehensive Assay v3 GX
        (MSI + TMB + HRD)', so the size steps down until the whole name fits in
        the space available. It is never shortened.
        """
        width = box[2] - box[0]
        available = box[3] - top

        for pt in range(int(S * 0.062), int(S * 0.022), -max(1, int(S * 0.002))):
            font = self.ImageFont.truetype(self.serif_path, pt)
            lines = self.wrap(draw, name, font, width)
            leading = int(pt * 1.22)
            if len(lines) <= 4 and len(lines) * leading <= available:
                break

        y = top
        for line in lines:
            draw.text((box[0], y), line, font=font, fill=INK)
            y += leading

    def wrap(self, draw, text, font, width):
        words, lines, current = text.split(), [], ''
        for word in words:
            trial = f'{current} {word}'.strip()
            if draw.textlength(trial, font=font) <= width or not current:
                current = trial
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines

    # ---------------------------------------------------------------- #
    # Category diagrams — one visual language, seven variations
    # ---------------------------------------------------------------- #

    def draw_motif(self, draw, product, box):
        seed = int(hashlib.md5(product.slug.encode()).hexdigest()[:8], 16)
        handler = {
            Product.Category.RELATIONSHIP: self.motif_helix,
            Product.Category.IMMIGRATION: self.motif_gate,
            Product.Category.PRENATAL: self.motif_nested,
            Product.Category.CLINICAL: self.motif_panel,
            Product.Category.WELLNESS: self.motif_wheel,
            Product.Category.ANCESTRY: self.motif_lineage,
        }.get(product.category, self.motif_specimen)
        handler(draw, box, seed)

    def _geom(self, box):
        x0, y0, x1, y1 = box
        return x0, y0, x1, y1, (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0), (y1 - y0)

    def _helix(self, draw, cx, top, span, amp, lw, turns, rungs, marked):
        """A double helix with real over/under weaving.

        Two opposite-phase sine waves drawn flat read as a stack of lens
        shapes, not as a helix. Depth is what sells it: each strand segment
        carries a z value, back segments are drawn first and lighter, front
        segments last. The strands then visibly pass behind one another.
        """
        steps = 300

        def strand(phase):
            pts = []
            for i in range(steps + 1):
                t = i / steps
                ang = t * turns * 2 * math.pi + phase
                pts.append((cx + amp * math.sin(ang), top + t * span,
                            math.cos(ang)))
            return pts

        a, b = strand(0.0), strand(math.pi)

        # Pass 1: everything behind. Pass 2: everything in front.
        for front in (False, True):
            for pts, base_colour in ((a, TEAL), (b, TEAL_SOFT)):
                run = []
                for x, y, z in pts + [(None, None, None)]:
                    in_pass = z is not None and ((z >= 0) == front)
                    if in_pass:
                        run.append((x, y))
                        continue
                    if len(run) > 1:
                        colour = base_colour if front else self._fade(base_colour)
                        draw.line(run, fill=colour,
                                  width=lw if front else max(2, int(lw * 0.8)),
                                  joint='curve')
                    run = []

            if not front:
                for i in range(rungs):
                    t = (i + 0.5) / rungs
                    y = top + t * span
                    ang = t * turns * 2 * math.pi
                    x0 = cx + amp * math.sin(ang)
                    x1 = cx + amp * math.sin(ang + math.pi)
                    hit = (i == marked)
                    draw.line((x0, y, x1, y),
                              fill=AMBER if hit else LINE,
                              width=max(1, int(lw * (0.9 if hit else 0.7))))
                    # Node dots only where the rung meets the strand nearest the
                    # viewer. Dotting every join made the figure read as noise.
                    if abs(math.cos(ang)) > 0.35 or hit:
                        front_x = x0 if math.cos(ang) >= 0 else x1
                        r = lw * (1.5 if hit else 1.15)
                        draw.ellipse((front_x - r, y - r, front_x + r, y + r),
                                     fill=AMBER if hit else TEAL)

    @staticmethod
    def _fade(colour, amount=0.55):
        """Mix a colour toward the paper, for strand segments sitting behind."""
        return tuple(int(c + (PAPER[i] - c) * amount) for i, c in enumerate(colour))

    def motif_helix(self, draw, box, seed):
        """Two strands with paired rungs — a relationship between two people."""
        _, _, _, _, cx, cy, w, h = self._geom(box)
        amp, span = w * 0.185, h * 0.96
        lw = max(2, int(w * 0.011))
        rungs = 10 + seed % 4
        self._helix(draw, cx, cy - span / 2, span, amp, lw,
                    turns=2.0, rungs=rungs, marked=seed % rungs)

    def motif_gate(self, draw, box, seed):
        """A strand crossing a border — immigration and legal work."""
        _, _, _, _, cx, cy, w, h = self._geom(box)
        lw = max(2, int(w * 0.009))
        gw, gh = w * 0.46, h * 0.62

        draw.rounded_rectangle((cx - gw / 2, cy - gh / 2, cx + gw / 2, cy + gh / 2),
                               radius=int(w * 0.02), outline=(194, 216, 209),
                               width=max(2, int(lw * 1.1)))
        ticks = 3 + seed % 3
        for i in range(1, ticks + 1):
            y = cy - gh / 2 + gh * i / (ticks + 1)
            draw.line((cx - gw / 2, y, cx - gw / 2 + gw * 0.10, y),
                      fill=LINE, width=lw)
            draw.line((cx + gw / 2 - gw * 0.10, y, cx + gw / 2, y),
                      fill=LINE, width=lw)

        amp = w * (0.13 + (seed % 4) * 0.012)
        span = h * 0.94
        top = cy - span / 2
        turns = 2.0 + (seed >> 4) % 2 * 0.5
        rungs = 9 + seed % 4
        self._helix(draw, cx, top, span, amp, lw,
                    turns=turns, rungs=rungs, marked=seed % rungs)

        # The border crossing itself, marked at entry or exit.
        r = lw * 2.0
        edge = cy - gh / 2 if seed % 2 else cy + gh / 2
        draw.ellipse((cx - r, edge - r, cx + r, edge + r), fill=AMBER)

    def motif_nested(self, draw, box, seed):
        """Nested arcs — one life inside another."""
        _, _, _, _, cx, cy, w, h = self._geom(box)
        lw = max(2, int(w * 0.009))
        base = min(w, h) * 0.40

        rings = 3 + seed % 2
        sweep = 300 + (seed % 3) * 18
        start = 90 + (seed % 4) * 14
        scales = [1.0 - i * (0.26 if rings == 3 else 0.20) for i in range(rings)]
        for i, scale in enumerate(scales):
            colour = LINE if i == 0 else (TEAL_SOFT if i % 2 else TEAL)
            r = base * scale
            draw.arc((cx - r, cy - r, cx + r, cy + r),
                     start=start, end=start + sweep,
                     fill=colour, width=lw if i else max(2, int(lw * 0.8)))

        r = base * 0.16
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=TEAL)

        ang = math.radians(start + sweep * (0.25 + (seed % 5) * 0.12))
        ring = base * scales[1]
        dot = lw * 1.7
        draw.ellipse((cx + ring * math.cos(ang) - dot, cy + ring * math.sin(ang) - dot,
                      cx + ring * math.cos(ang) + dot, cy + ring * math.sin(ang) + dot),
                     fill=AMBER)

    def motif_panel(self, draw, box, seed):
        """A genetic read-out.

        Fourteen of the thirty tests are clinical, so a single diagram repeated
        fourteen times would make them indistinguishable in a shopping grid —
        which is the whole job of a catalogue image. Three read-out forms,
        chosen deterministically from the slug, plus seeded density and one
        amber called marker, give each test its own fingerprint while keeping
        them obviously the same family.
        """
        variant = seed % 3
        if variant == 0:
            self._panel_bands(draw, box, seed)
        elif variant == 1:
            self._panel_lanes(draw, box, seed)
        else:
            self._panel_cluster(draw, box, seed)

    @staticmethod
    def _rand(state):
        state = (state * 1103515245 + 12345) & 0x7FFFFFFF
        return state, state

    def _panel_bands(self, draw, box, seed):
        """Horizontal marker calls across a panel."""
        _, _, _, _, cx, cy, w, h = self._geom(box)
        lw = max(2, int(w * 0.008))
        rows = 6 + seed % 4
        cols = 7 + (seed >> 3) % 4
        gw, gh = w * 0.80, h * 0.68
        left, top = cx - gw / 2, cy - gh / 2
        cw, ch = gw / cols, gh / rows

        for r in range(rows):
            y = top + r * ch + ch / 2
            draw.line((left, y, left + gw, y), fill=(238, 246, 243), width=lw)

        rnd = seed | 1
        hit_r, hit_c = seed % rows, (seed >> 7) % cols
        for r in range(rows):
            for c in range(cols):
                rnd, _ = self._rand(rnd)
                if rnd % 100 < 34:
                    continue
                x = left + c * cw + cw / 2
                y = top + r * ch + ch / 2
                length = cw * (0.28 + (rnd >> 8 & 7) / 20)
                called = (r == hit_r and c == hit_c)
                colour = AMBER if called else (TEAL if (rnd >> 5) % 3 else TEAL_SOFT)
                draw.line((x - length, y, x + length, y),
                          fill=colour, width=int(lw * (2.0 if called else 1.5)))

        draw.line((left, top, left, top + gh), fill=LINE, width=lw)
        draw.line((left + gw, top, left + gw, top + gh), fill=LINE, width=lw)

    def _panel_lanes(self, draw, box, seed):
        """Vertical lanes, read like a gel."""
        _, _, _, _, cx, cy, w, h = self._geom(box)
        lw = max(2, int(w * 0.008))
        lanes = 6 + seed % 3
        gw, gh = w * 0.76, h * 0.74
        left, top = cx - gw / 2, cy - gh / 2
        lane_w = gw / lanes

        rnd = seed | 1
        hit = (seed >> 5) % lanes
        for i in range(lanes):
            x = left + i * lane_w + lane_w / 2
            draw.line((x, top, x, top + gh), fill=(238, 246, 243), width=lw)
            rnd, _ = self._rand(rnd)
            bands = 2 + rnd % 4
            for b in range(bands):
                rnd, _ = self._rand(rnd)
                y = top + gh * (0.08 + (rnd % 84) / 100)
                half = lane_w * 0.34
                called = (i == hit and b == 0)
                colour = AMBER if called else (TEAL if b % 2 else TEAL_SOFT)
                draw.line((x - half, y, x + half, y),
                          fill=colour, width=int(lw * (2.2 if called else 1.7)))

        draw.line((left, top + gh, left + gw, top + gh), fill=LINE, width=lw)

    def _panel_cluster(self, draw, box, seed):
        """Variant calls plotted against a baseline."""
        _, _, _, _, cx, cy, w, h = self._geom(box)
        lw = max(2, int(w * 0.008))
        gw, gh = w * 0.80, h * 0.66
        left, top = cx - gw / 2, cy - gh / 2
        base = top + gh

        draw.line((left, base, left + gw, base), fill=LINE, width=lw)
        draw.line((left, top, left, base), fill=LINE, width=lw)
        for i in range(1, 3):
            y = base - gh * i / 3
            draw.line((left, y, left + gw, y), fill=(238, 246, 243), width=lw)

        rnd = seed | 1
        points = 13 + seed % 6
        hit = (seed >> 9) % points
        for i in range(points):
            rnd, _ = self._rand(rnd)
            x = left + gw * (i + 0.5) / points
            height = gh * (0.12 + (rnd % 80) / 100)
            colour = AMBER if i == hit else (TEAL if i % 2 else TEAL_SOFT)
            draw.line((x, base, x, base - height),
                      fill=colour, width=int(lw * (2.2 if i == hit else 1.6)))
            r = lw * (2.0 if i == hit else 1.4)
            draw.ellipse((x - r, base - height - r, x + r, base - height + r),
                         fill=colour)

    def motif_wheel(self, draw, box, seed):
        """A metabolic wheel — many inputs, one profile."""
        _, _, _, _, cx, cy, w, h = self._geom(box)
        lw = max(2, int(w * 0.009))
        outer = min(w, h) * 0.42
        spokes = 16

        draw.ellipse((cx - outer, cy - outer, cx + outer, cy + outer),
                     outline=LINE, width=lw)
        inner = outer * 0.30
        draw.ellipse((cx - inner, cy - inner, cx + inner, cy + inner),
                     outline=TEAL, width=lw)

        rnd = seed
        for i in range(spokes):
            ang = i / spokes * 2 * math.pi - math.pi / 2
            rnd = (rnd * 1103515245 + 12345) & 0x7FFFFFFF
            reach = inner + (outer - inner) * (0.30 + (rnd % 70) / 100)
            draw.line((cx + inner * math.cos(ang), cy + inner * math.sin(ang),
                       cx + reach * math.cos(ang), cy + reach * math.sin(ang)),
                      fill=TEAL if i % 2 else TEAL_SOFT, width=lw)
            r = lw * 1.5
            draw.ellipse((cx + reach * math.cos(ang) - r,
                          cy + reach * math.sin(ang) - r,
                          cx + reach * math.cos(ang) + r,
                          cy + reach * math.sin(ang) + r),
                         fill=TEAL if i % 2 else TEAL_SOFT)

    def motif_lineage(self, draw, box, seed):
        """A line of descent.

        Replaced a set of stacked arcs that read as a rainbow rather than as
        ancestry. A branching tree says lineage without needing a caption.
        """
        _, _, _, _, cx, cy, w, h = self._geom(box)
        lw = max(2, int(w * 0.009))
        gh = h * 0.78
        top = cy - gh / 2
        levels = 4
        spread = w * 0.74

        def node(x, y, colour, size=1.0):
            r = lw * 1.9 * size
            draw.ellipse((x - r, y - r, x + r, y + r), fill=colour)

        rows = []
        for level in range(levels):
            count = 2 ** level
            y = top + gh * level / (levels - 1)
            width = spread * (level / (levels - 1)) if levels > 1 else 0
            xs = ([cx] if count == 1 else
                  [cx - width / 2 + width * i / (count - 1) for i in range(count)])
            rows.append((y, xs))

        for level in range(levels - 1):
            y0, xs0 = rows[level]
            y1, xs1 = rows[level + 1]
            for i, x0 in enumerate(xs0):
                for x1 in xs1[i * 2:i * 2 + 2]:
                    draw.line((x0, y0, x1, y1), fill=LINE, width=lw)

        highlight = seed % (2 ** (levels - 1))
        for level, (y, xs) in enumerate(rows):
            for i, x in enumerate(xs):
                on_path = (i == highlight >> (levels - 1 - level))
                colour = TEAL if on_path else (208, 226, 220)
                node(x, y, colour, 1.15 if on_path else 0.85)

        y, xs = rows[-1]
        node(xs[highlight], y, AMBER, 1.3)

    def motif_specimen(self, draw, box, seed):
        """A sealed swab in its tube — what the customer actually handles."""
        _, _, _, _, cx, cy, w, h = self._geom(box)
        lw = max(2, int(w * 0.009))
        tw, th = w * 0.17, h * 0.74
        left, top = cx - tw / 2, cy - th / 2

        draw.rounded_rectangle((left, top, left + tw, top + th),
                               radius=int(tw * 0.42), outline=TEAL, width=lw)
        cap = th * 0.17
        draw.rounded_rectangle((left - tw * 0.09, top, left + tw * 1.09, top + cap),
                               radius=int(tw * 0.14), fill=TEAL)

        depth = 0.68 + (seed % 4) * 0.035
        draw.line((cx, top + cap * 1.5, cx, top + th * depth),
                  fill=TEAL_SOFT, width=max(2, int(lw * 1.2)))
        head = tw * (0.26 + (seed % 3) * 0.035)
        draw.ellipse((cx - head, top + th * (depth - 0.04),
                      cx + head, top + th * (depth - 0.04) + head * 2.1),
                     fill=TEAL_SOFT)

        marks = 3 + seed % 3
        for i in range(marks):
            y = top + th * (0.34 + i * 0.072)
            draw.line((left + tw * 0.22, y, left + tw * 0.78, y),
                      fill=LINE, width=max(1, int(lw * 0.8)))
        tick = top + th * (0.34 + (seed % marks) * 0.072)
        draw.line((left + tw * 0.22, tick, left + tw * 0.62, tick),
                  fill=AMBER, width=max(2, int(lw * 1.1)))

    # ---------------------------------------------------------------- #

    def contact_sheet(self, images, cols=5, cell=300, gap=18):
        rows = math.ceil(len(images) / cols)
        W = cols * cell + (cols + 1) * gap
        H = rows * cell + (rows + 1) * gap
        sheet = self.Image.new('RGB', (W, H), (255, 255, 255))
        for i, image in enumerate(images):
            r, c = divmod(i, cols)
            sheet.paste(image.resize((cell, cell), self.Image.LANCZOS),
                        (gap + c * (cell + gap), gap + r * (cell + gap)))
        return sheet