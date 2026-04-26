from django.db import migrations


class Migration(migrations.Migration):
    """
    Merge the task-contract branch and the attachment/governance branch.

    Both branches legitimately diverged from 0084 and are required by the
    current V21 codebase. This merge restores a single leaf so runtime
    migration planning and test database creation no longer fail with
    conflicting leaf nodes.
    """

    dependencies = [
        ("core", "0085_task_contract_and_activity_snapshot"),
        ("core", "0088_v20_attachment_forensics_and_remote_escalations"),
    ]

    operations = []
