"""Drop the backfill default, making the document type a required choice.

``0014`` added the columns with ``default='DIPLOMA'`` purely to backfill existing
rows. Keeping that default would let a new template or assignment silently become
a diploma; the caller must decide instead. Column-level ``NOT NULL`` is unchanged —
only the default goes away.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('diplomas', '0014_document_types'),
    ]

    operations = [
        migrations.AlterField(
            model_name='assignmentmodel',
            name='document_type',
            field=models.CharField(choices=[('DIPLOMA', 'Диплом'), ('THANK_YOU', 'Благодарность')], max_length=32),
        ),
        migrations.AlterField(
            model_name='templatemodel',
            name='type',
            field=models.CharField(choices=[('DIPLOMA', 'Диплом'), ('THANK_YOU', 'Благодарность')], max_length=32),
        ),
    ]
