"""Seed partner laboratories, their certificates, and the test catalogue.

    python manage.py seed_dnalab                      # seed everything
    python manage.py seed_dnalab --labs-only
    python manage.py seed_dnalab --products-only
    python manage.py seed_dnalab --placeholder-certs   # generate stand-in certs
    python manage.py seed_dnalab --activate-labs       # seed labs switched on
    python manage.py seed_dnalab --file path/to/other.json
    python manage.py seed_dnalab --dry-run

Idempotent: every record is matched on its slug with update_or_create, so
re-running after an edit updates rather than duplicates. Nothing is deleted.

Images are optional. Put real files in core/seed_assets/logos/ and
core/seed_assets/certificates/ and the command picks them up by filename.
"""

import json
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.models import (
    CompanyCredential, LabCertification, PartnerLab, Product,
)


class Command(BaseCommand):
    help = 'Seed partner laboratories, certificates and products from seed_data.json'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            help='Path to the seed JSON. Defaults to core/seed_data.json.',
        )
        parser.add_argument('--labs-only', action='store_true')
        parser.add_argument('--products-only', action='store_true')
        parser.add_argument(
            '--placeholder-certs', action='store_true',
            help='Generate a stand-in certificate image where no real file is '
                 'available. Useful for checking the layout — replace with the '
                 'real scans before going live.',
        )
        parser.add_argument(
            '--activate-labs', action='store_true',
            help='Seed labs with is_active=True. Off by default so nothing '
                 'goes public before you have verified the agreement.',
        )
        parser.add_argument(
            '--available-products', action='store_true',
            help='Seed products with available=True. Off by default so no '
                 'placeholder price can reach a customer.',
        )
        parser.add_argument('--dry-run', action='store_true')

    # ------------------------------------------------------------------ #

    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        self.base_dir = Path(__file__).resolve().parents[2]  # the core/ app dir

        path = Path(options['file']) if options['file'] else self.base_dir / 'seed_data.json'
        if not path.exists():
            raise CommandError(f'Seed file not found: {path}')

        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except json.JSONDecodeError as exc:
            raise CommandError(f'{path} is not valid JSON: {exc}')

        self.stdout.write(f'Reading {path}')
        if self.dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN — nothing will be saved'))

        do_labs = not options['products_only']
        do_products = not options['labs_only']

        with transaction.atomic():
            if do_labs:
                self.seed_labs(data.get('labs', []), options)
            if do_labs:
                self.seed_credentials(data.get('company_credentials', []), options)
            if do_products:
                self.seed_products(data.get('products', []), options)

            if self.dry_run:
                transaction.set_rollback(True)

        self.report(options)

    # ------------------------------------------------------------------ #

    def seed_labs(self, labs, options):
        self.lab_created = self.lab_updated = self.cert_count = 0
        self.missing_accreditations = []

        for entry in labs:
            slug = entry.get('slug')
            if not slug:
                self.stdout.write(self.style.WARNING('  skipped a lab with no slug'))
                continue

            lab, created = PartnerLab.objects.update_or_create(
                slug=slug,
                defaults={
                    'name': entry.get('name', slug),
                    'country': entry.get('country', 'GB'),
                    'city': entry.get('city', ''),
                    'summary': entry.get('summary', ''),
                    'description': entry.get('description', ''),
                    'accreditations': entry.get('accreditations', ''),
                    'handles_legal_tests': entry.get('handles_legal_tests', False),
                    'website': entry.get('website', ''),
                    'display_order': entry.get('display_order', 0),
                    'is_active': options['activate_labs'] or entry.get('is_active', False),
                },
            )

            if created:
                self.lab_created += 1
            else:
                self.lab_updated += 1

            if not entry.get('accreditations'):
                self.missing_accreditations.append(lab.name)

            self.attach_logo(lab, entry.get('logo'))

            for cert in entry.get('certificates', []):
                self.seed_certificate(lab, cert, options)

            flag = 'live' if lab.is_active else 'hidden'
            verb = 'created' if created else 'updated'
            self.stdout.write(f'  lab   {verb:8} {lab.name}  [{flag}]')

    def seed_credentials(self, entries, options):
        """Documents the company itself holds — kept separate from the labs'."""
        self.credential_count = 0
        for entry in entries:
            slug = entry.get('slug')
            title = entry.get('title')
            if not title:
                continue

            credential, created = CompanyCredential.objects.update_or_create(
                title=title,
                defaults={
                    'kind': entry.get('kind', CompanyCredential.Kind.OTHER),
                    'issuer': entry.get('issuer', ''),
                    'summary': entry.get('summary', ''),
                    'reference': entry.get('reference', ''),
                    'issued_year': entry.get('issued_year') or None,
                    'valid_until': entry.get('valid_until') or None,
                    'display_order': entry.get('display_order', 0),
                    'is_active': entry.get('is_active', True),
                },
            )

            if not self.dry_run and not credential.image and entry.get('image'):
                source = self.base_dir / 'seed_assets' / 'certificates' / entry['image']
                if source.exists():
                    with source.open('rb') as fh:
                        credential.image.save(entry['image'], File(fh), save=True)

            self.credential_count += 1
            verb = 'created' if created else 'updated'
            flag = 'live' if credential.is_active else 'hidden'
            self.stdout.write(f'  cred  {verb:8} {credential.title}  [{flag}]')

    def attach_logo(self, lab, filename):
        """Attach a logo if a matching file exists; never fail if it doesn't."""
        if not filename or lab.logo or self.dry_run:
            return
        source = self.base_dir / 'seed_assets' / 'logos' / filename
        if not source.exists():
            return
        with source.open('rb') as fh:
            lab.logo.save(filename, File(fh), save=True)

    def seed_certificate(self, lab, entry, options):
        title = entry.get('title')
        if not title:
            return

        certificate, created = LabCertification.objects.get_or_create(
            lab=lab,
            title=title,
            defaults={
                'kind': entry.get('kind', LabCertification.Kind.ACCREDITATION),
                'issuing_body': entry.get('issuing_body', ''),
                'reference': entry.get('reference', ''),
                'valid_until': entry.get('valid_until') or None,
                'display_order': entry.get('display_order', 0),
                'is_active': entry.get('is_active', True),
            },
        )

        if self.dry_run:
            self.cert_count += 1
            return

        if not certificate.image:
            image = self.certificate_image(lab, entry, options)
            if image:
                name, content = image
                certificate.image.save(name, content, save=True)
            else:
                # An ImageField is required, so a certificate with no image is
                # not useful — remove it rather than leave a broken record.
                if created:
                    certificate.delete()
                    self.stdout.write(self.style.WARNING(
                        f'  cert  skipped  {lab.name} — {title} (no image; '
                        f'add the scan or pass --placeholder-certs)'
                    ))
                return

        self.cert_count += 1
        self.stdout.write(f'  cert  ok       {lab.name} — {title}')

    def certificate_image(self, lab, entry, options):
        """Return (filename, File) for a certificate, or None."""
        filename = entry.get('image')
        if filename:
            source = self.base_dir / 'seed_assets' / 'certificates' / filename
            if source.exists():
                return filename, File(source.open('rb'))

        if not options['placeholder_certs']:
            return None
        return self.placeholder_image(lab, entry)

    def placeholder_image(self, lab, entry):
        """A plainly-marked stand-in, so the layout can be checked.

        Deliberately ugly and labelled: a placeholder that looks like a real
        certificate is the kind of thing that quietly reaches production.
        """
        from io import BytesIO

        from django.core.files.base import ContentFile
        from PIL import Image, ImageDraw

        width, height = 620, 840
        image = Image.new('RGB', (width, height), '#FFFFFF')
        draw = ImageDraw.Draw(image)
        draw.rectangle([14, 14, width - 15, height - 15], outline='#D98A14', width=4)
        draw.text((width // 2, 150), 'PLACEHOLDER', fill='#D98A14', anchor='mm')
        draw.text((width // 2, 200), 'NOT A REAL CERTIFICATE', fill='#D98A14', anchor='mm')
        draw.line([110, 250, width - 110, 250], fill='#DAE4E6', width=2)
        draw.text((width // 2, 330), lab.name, fill='#063B49', anchor='mm')
        draw.text((width // 2, 380), entry.get('title', ''), fill='#0A6B80', anchor='mm')
        draw.text((width // 2, 430), entry.get('issuing_body', ''), fill='#4A6B74', anchor='mm')
        draw.text((width // 2, height - 140),
                  'Replace with the scanned certificate', fill='#4A6B74', anchor='mm')

        buffer = BytesIO()
        image.save(buffer, 'PNG')
        return f'placeholder-{lab.slug}.png', ContentFile(buffer.getvalue())

    # ------------------------------------------------------------------ #

    def seed_products(self, products, options):
        self.product_created = self.product_updated = 0
        self.zero_price = []
        self.no_sample_type = []
        self.needs_clinic = []

        for entry in products:
            slug = entry.get('slug')
            if not slug:
                continue

            lab = None
            if entry.get('lab'):
                lab = PartnerLab.objects.filter(slug=entry['lab']).first()
                if lab is None:
                    self.stdout.write(self.style.WARNING(
                        f"  prod  warning  {slug}: no lab with slug '{entry['lab']}'"
                    ))

            product, created = Product.objects.update_or_create(
                slug=slug,
                defaults={
                    'name': entry.get('name', slug),
                    'description': entry.get('description', ''),
                    'price': entry.get('price', 0),
                    'discounted_price': entry.get('discounted_price'),
                    'category': entry.get('category', Product.Category.OTHER),
                    'sample_type': entry.get('sample_type', ''),
                    'partner_lab': lab,
                    # --available-products never publishes a product with no price.
                    'available': bool(entry.get('price')) and (
                        options['available_products'] or entry.get('available', False)
                    ),
                },
            )

            if created:
                self.product_created += 1
            else:
                self.product_updated += 1

            if not product.price:
                self.zero_price.append(product.name)
            if not product.sample_type:
                self.no_sample_type.append(product.name)
            if product.needs_clinical_collection:
                self.needs_clinic.append(product.name)

            flag = 'available' if product.available else 'hidden'
            verb = 'created' if created else 'updated'
            self.stdout.write(f'  prod  {verb:8} {product.name}  [{flag}]')

    # ------------------------------------------------------------------ #

    def report(self, options):
        self.stdout.write('')
        if not options['products_only']:
            self.stdout.write(self.style.SUCCESS(
                f'Labs: {self.lab_created} created, {self.lab_updated} updated, '
                f'{self.cert_count} lab documents, '
                f'{getattr(self, "credential_count", 0)} company credentials'
            ))
        if not options['labs_only']:
            self.stdout.write(self.style.SUCCESS(
                f'Products: {self.product_created} created, {self.product_updated} updated'
            ))

        self.stdout.write('')
        self.stdout.write('Before any of this goes live:')

        if not options['products_only'] and getattr(self, 'missing_accreditations', None):
            names = ', '.join(self.missing_accreditations)
            self.stdout.write(self.style.WARNING(
                f'  - No accreditations recorded for: {names}. Add only what '
                f'each lab actually holds — they display as credentials.'
            ))

        if not options['products_only']:
            hidden = PartnerLab.objects.filter(is_active=False).count()
            if hidden:
                self.stdout.write(self.style.WARNING(
                    f'  - {hidden} lab(s) are hidden. Switch one on only once you '
                    f'hold a current written agreement with it.'
                ))

        if not options['labs_only']:
            if self.zero_price:
                self.stdout.write(self.style.ERROR(
                    f'  - {len(self.zero_price)} product(s) have no price and '
                    f'must not go live: {", ".join(self.zero_price)}'
                ))
            if self.no_sample_type:
                self.stdout.write(self.style.WARNING(
                    f'  - {len(self.no_sample_type)} product(s) have no sample '
                    f'type set: {", ".join(self.no_sample_type)}. The site uses '
                    f'this to warn customers when a test cannot be collected at '
                    f'the Lahore office.'
                ))
            if self.needs_clinic:
                self.stdout.write(self.style.WARNING(
                    f'  - {len(self.needs_clinic)} product(s) need a blood or '
                    f'tissue sample, which your Lahore office does not collect. '
                    f'Confirm your clinical collection arrangement before making '
                    f'these available.'
                ))

        if options['placeholder_certs']:
            self.stdout.write(self.style.WARNING(
                '  - Placeholder certificate images were generated. Replace '
                'them with the real scans.'
            ))
