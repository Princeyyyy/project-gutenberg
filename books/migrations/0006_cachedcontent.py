from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('books', '0005_book_editors'),
    ]

    operations = [
        migrations.CreateModel(
            name='CachedContent',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('format_mime_type', models.CharField(max_length=64)),
                ('storage_url', models.URLField(blank=True, default='', max_length=512)),
                ('status', models.CharField(
                    choices=[
                        ('pending', 'Pending'),
                        ('fetching', 'Fetching'),
                        ('ready', 'Ready'),
                        ('failed', 'Failed'),
                    ],
                    default='pending',
                    max_length=10,
                )),
                ('error_message', models.TextField(blank=True, default='')),
                ('mirror_used', models.CharField(blank=True, default='', max_length=256)),
                ('file_size_bytes', models.PositiveIntegerField(blank=True, null=True)),
                ('requested_at', models.DateTimeField(auto_now_add=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('book', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='cached_contents',
                    to='books.book',
                )),
            ],
            options={
                'verbose_name_plural': 'cached contents',
                'unique_together': {('book', 'format_mime_type')},
            },
        ),
        # Index on status for the worker's polling query
        migrations.AddIndex(
            model_name='cachedcontent',
            index=models.Index(
                fields=['status', 'requested_at'],
                name='books_cached_status_req_idx',
            ),
        ),
    ]
