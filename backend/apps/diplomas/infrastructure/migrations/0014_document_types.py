"""Introduce document types.

Three changes, in one migration so the schema is never half-typed:

* ``TemplateModel.type`` — which kind of document a template produces. Existing
  templates are backfilled as ``DIPLOMA``, which is what every one of them is.
* ``AssignmentModel.document_type`` — which slot of a nomination an assignment
  fills, backfilled the same way. The unique constraint moves from
  ``(competition, category)`` to ``(competition, category, document_type)``, so a
  nomination can hold a diploma template *and* a thank-you template without the
  row shape changing.
* ``diplomas_issued_document`` — generated documents that carry neither a number
  nor a verification token. ``diplomas_diploma`` is deliberately untouched: its
  number and token stay ``NOT NULL``, so the public register keeps its invariants.

The backfill default is removed again in ``0015`` so the columns are genuinely
required from here on.
"""

import apps.diplomas.infrastructure.models.base
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('diplomas', '0013_diplomanumbersequencemodel'),
    ]

    operations = [
        migrations.CreateModel(
            name='IssuedDocumentModel',
            fields=[
                ('id', models.UUIDField(default=apps.diplomas.infrastructure.models.base.uuid7, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ('updated_at', models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ('deleted_at', models.DateTimeField(blank=True, default=None, editable=False, null=True)),
                ('version', models.PositiveIntegerField(default=1, editable=False)),
                ('document_type', models.CharField(choices=[('DIPLOMA', 'Диплом'), ('THANK_YOU', 'Благодарность')], max_length=32)),
                ('competition_id', models.UUIDField()),
                ('submission_id', models.UUIDField()),
                ('template_id', models.UUIDField()),
                ('snapshot', models.JSONField(blank=True, default=dict)),
                ('pdf_path', models.CharField(blank=True, default='', max_length=1024)),
                ('published_at', models.DateTimeField(blank=True, default=None, null=True)),
            ],
            options={
                'verbose_name': 'issued document',
                'verbose_name_plural': 'issued documents',
                'db_table': 'diplomas_issued_document',
                'abstract': False,
            },
        ),
        migrations.AlterModelOptions(
            name='templatemodel',
            options={'verbose_name': 'document template', 'verbose_name_plural': 'document templates'},
        ),
        migrations.RemoveConstraint(
            model_name='assignmentmodel',
            name='diplomas_unique_assignment',
        ),
        migrations.AddField(
            model_name='assignmentmodel',
            name='document_type',
            field=models.CharField(choices=[('DIPLOMA', 'Диплом'), ('THANK_YOU', 'Благодарность')], default='DIPLOMA', max_length=32),
        ),
        migrations.AddField(
            model_name='templatemodel',
            name='type',
            field=models.CharField(choices=[('DIPLOMA', 'Диплом'), ('THANK_YOU', 'Благодарность')], default='DIPLOMA', max_length=32),
        ),
        migrations.AddIndex(
            model_name='assignmentmodel',
            index=models.Index(fields=['competition_id', 'document_type'], name='diplomas_as_competi_80dbda_idx'),
        ),
        migrations.AddIndex(
            model_name='templatemodel',
            index=models.Index(fields=['type'], name='diplomas_te_type_cda8c6_idx'),
        ),
        migrations.AddConstraint(
            model_name='assignmentmodel',
            constraint=models.UniqueConstraint(condition=models.Q(('deleted_at__isnull', True)), fields=('competition_id', 'category_id', 'document_type'), name='diplomas_unique_assignment_per_type'),
        ),
        migrations.AddConstraint(
            model_name='assignmentmodel',
            constraint=models.CheckConstraint(condition=models.Q(('document_type__in', ['DIPLOMA', 'THANK_YOU'])), name='diplomas_assignment_type_valid'),
        ),
        migrations.AddConstraint(
            model_name='templatemodel',
            constraint=models.CheckConstraint(condition=models.Q(('type__in', ['DIPLOMA', 'THANK_YOU'])), name='diplomas_template_type_valid'),
        ),
        migrations.AddIndex(
            model_name='issueddocumentmodel',
            index=models.Index(fields=['created_at'], name='diplomas_is_created_ef2b26_idx'),
        ),
        migrations.AddIndex(
            model_name='issueddocumentmodel',
            index=models.Index(fields=['updated_at'], name='diplomas_is_updated_9194d6_idx'),
        ),
        migrations.AddIndex(
            model_name='issueddocumentmodel',
            index=models.Index(fields=['deleted_at'], name='diplomas_is_deleted_6a1c9a_idx'),
        ),
        migrations.AddIndex(
            model_name='issueddocumentmodel',
            index=models.Index(fields=['competition_id'], name='diplomas_is_competi_270da0_idx'),
        ),
        migrations.AddIndex(
            model_name='issueddocumentmodel',
            index=models.Index(fields=['submission_id'], name='diplomas_is_submiss_48a7a0_idx'),
        ),
        migrations.AddIndex(
            model_name='issueddocumentmodel',
            index=models.Index(fields=['document_type'], name='diplomas_is_documen_5963bc_idx'),
        ),
        migrations.AddConstraint(
            model_name='issueddocumentmodel',
            constraint=models.CheckConstraint(condition=models.Q(('version__gte', 1)), name='diplomas_issueddocumentmodel_version_positive'),
        ),
        migrations.AddConstraint(
            model_name='issueddocumentmodel',
            constraint=models.UniqueConstraint(condition=models.Q(('deleted_at__isnull', True)), fields=('submission_id', 'document_type'), name='diplomas_issued_unique_per_performance_type'),
        ),
        migrations.AddConstraint(
            model_name='issueddocumentmodel',
            constraint=models.CheckConstraint(condition=models.Q(('document_type__in', ['DIPLOMA', 'THANK_YOU'])), name='diplomas_issued_document_type_valid'),
        ),
    ]
