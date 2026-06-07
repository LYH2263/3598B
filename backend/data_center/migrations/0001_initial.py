from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='DataTask',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('task_type', models.CharField(choices=[('import', '导入'), ('export', '导出')], max_length=20, verbose_name='任务类型')),
                ('data_type', models.CharField(choices=[('users', '用户'), ('recharges', '充值记录'), ('consumptions', '消费记录'), ('utility_bills', '水电账单')], max_length=30, verbose_name='数据类型')),
                ('status', models.CharField(choices=[('submitted', '提交中'), ('running', '进行中'), ('success', '成功'), ('failed', '失败'), ('partial', '部分成功')], default='submitted', max_length=20, verbose_name='状态')),
                ('progress_percent', models.IntegerField(default=0, verbose_name='进度百分比')),
                ('file_name', models.CharField(blank=True, default='', max_length=255, verbose_name='文件名')),
                ('file_hash', models.CharField(blank=True, db_index=True, default='', max_length=64, verbose_name='文件哈希（幂等控制）')),
                ('file_format', models.CharField(choices=[('csv', 'CSV'), ('xlsx', 'XLSX')], default='csv', max_length=10, verbose_name='文件格式')),
                ('params', models.JSONField(blank=True, default=dict, verbose_name='任务参数（筛选条件、字段选择等）')),
                ('result_file_path', models.CharField(blank=True, default='', max_length=500, verbose_name='结果文件路径')),
                ('error_file_path', models.CharField(blank=True, default='', max_length=500, verbose_name='错误明细文件路径')),
                ('total_rows', models.IntegerField(default=0, verbose_name='总行数')),
                ('success_rows', models.IntegerField(default=0, verbose_name='成功行数')),
                ('skipped_rows', models.IntegerField(default=0, verbose_name='跳过行数（幂等）')),
                ('failed_rows', models.IntegerField(default=0, verbose_name='失败行数')),
                ('error_message', models.TextField(blank=True, default='', verbose_name='错误信息')),
                ('preview_data', models.JSONField(blank=True, default=dict, verbose_name='预校验预览数据')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('finished_at', models.DateTimeField(blank=True, null=True, verbose_name='完成时间')),
                ('operator', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='data_tasks', to='auth.user', verbose_name='操作人')),
                ('parent_task', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='rerun_tasks', to='data_center.datatask', verbose_name='重跑来源任务')),
            ],
            options={
                'verbose_name': '数据任务',
                'verbose_name_plural': '数据任务',
                'db_table': 'data_tasks',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='ImportRowError',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('row_number', models.IntegerField(verbose_name='行号')),
                ('row_data', models.JSONField(default=dict, verbose_name='原始行数据')),
                ('error_messages', models.JSONField(default=list, verbose_name='错误信息列表')),
                ('is_corrected', models.BooleanField(default=False, verbose_name='是否已修正')),
                ('corrected_data', models.JSONField(blank=True, default=dict, verbose_name='修正后数据')),
                ('is_idempotent_skip', models.BooleanField(default=False, verbose_name='是否幂等跳过')),
                ('imported', models.BooleanField(default=False, verbose_name='是否已成功导入')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('task', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='row_errors', to='data_center.datatask', verbose_name='所属任务')),
            ],
            options={
                'verbose_name': '导入行错误',
                'verbose_name_plural': '导入行错误',
                'db_table': 'import_row_errors',
                'ordering': ['row_number'],
                'unique_together': {('task', 'row_number')},
            },
        ),
    ]
