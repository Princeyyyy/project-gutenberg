"""Pre-warm the content cache for the most popular books.

Creates CachedContent records with status=PENDING for the top-N books
by download_count, which the fetch worker then picks up automatically.
Designed to run via Heroku Scheduler as a weekly job.

Usage:
    python manage.py prewarm_cache              # default top 100
    python manage.py prewarm_cache --top=500    # top 500 books
    python manage.py prewarm_cache --format=epub --format=txt
"""

import logging

from django.core.management.base import BaseCommand

from books.models import Book, CachedContent, Format

logger = logging.getLogger(__name__)

DEFAULT_FORMATS = ['application/epub+zip']


class Command(BaseCommand):
    help = (
        'Pre-warm the content cache by creating pending fetch requests '
        'for the most popular books.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--top',
            type=int,
            default=100,
            help='Number of most-downloaded books to pre-warm (default: 100).',
        )
        parser.add_argument(
            '--format',
            action='append',
            dest='formats',
            help=(
                'MIME types to pre-warm (can be specified multiple times). '
                'Default: application/epub+zip'
            ),
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be pre-warmed without creating records.',
        )

    def handle(self, *args, **options):
        top_n = options['top']
        formats = options['formats'] or DEFAULT_FORMATS
        dry_run = options['dry_run']

        self.stdout.write(
            f'Pre-warming cache for top {top_n} books, '
            f'formats: {", ".join(formats)}'
            f'{" (DRY RUN)" if dry_run else ""}'
        )

        # Get the top N books by download count
        top_books = (
            Book.objects
            .exclude(download_count__isnull=True)
            .exclude(title__isnull=True)
            .order_by('-download_count')[:top_n]
        )

        created_count = 0
        skipped_count = 0
        not_available_count = 0

        for book in top_books:
            for mime_type in formats:
                # Check if this format exists for the book
                format_exists = Format.objects.filter(
                    book=book,
                    mime_type__startswith=mime_type.split(';')[0],
                ).exists()

                if not format_exists:
                    not_available_count += 1
                    continue

                # Get the actual mime_type from the format entry
                format_entry = Format.objects.filter(
                    book=book,
                    mime_type__startswith=mime_type.split(';')[0],
                ).first()

                # Check if already cached or pending
                existing = CachedContent.objects.filter(
                    book=book,
                    format_mime_type=format_entry.mime_type,
                ).first()

                if existing and existing.status in (
                    CachedContent.Status.READY,
                    CachedContent.Status.PENDING,
                    CachedContent.Status.FETCHING,
                ):
                    skipped_count += 1
                    continue

                if dry_run:
                    self.stdout.write(
                        f'  Would pre-warm: {book.gutenberg_id} '
                        f'"{book.title[:50]}" ({format_entry.mime_type})'
                    )
                    created_count += 1
                    continue

                # Create or reset the cached content record
                if existing:
                    # Reset a previously failed attempt
                    existing.status = CachedContent.Status.PENDING
                    existing.error_message = ''
                    existing.save(update_fields=['status', 'error_message'])
                else:
                    CachedContent.objects.create(
                        book=book,
                        format_mime_type=format_entry.mime_type,
                        status=CachedContent.Status.PENDING,
                    )

                created_count += 1

        action = 'Would create' if dry_run else 'Created'
        self.stdout.write(self.style.SUCCESS(
            f'\n{action} {created_count} pending fetch requests. '
            f'Skipped {skipped_count} (already cached/pending). '
            f'{not_available_count} format(s) not available.'
        ))

        if not dry_run and created_count > 0:
            self.stdout.write(
                'The fetch worker will pick these up automatically.'
            )
