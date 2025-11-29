from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('analytics', '0007_auto_create_preset_funnels'),
    ]

    operations = [
        migrations.CreateModel(
            name='IssueLifecycle',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('NEW', 'Новая'), ('PERSISTENT', 'Сохраняется'), ('IMPROVED', 'Улучшилась'), ('RESOLVED', 'Решена'), ('REGRESSED', 'Регресс')], max_length=20)),
                ('impact_change', models.FloatField(default=0.0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('issue', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lifecycles', to='analytics.uxissue')),
                ('version_first_seen', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='issues_first_seen', to='analytics.productversion')),
                ('version_resolved', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='issues_resolved', to='analytics.productversion')),
            ],
        ),
    ]
