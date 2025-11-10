from django.db import migrations

def seed_positions(apps, schema_editor):
    Position = apps.get_model("profiles", "Position")
    data = [
        # minimal 4-line taxonomy
        {"key": "gk", "name": "Goalkeeper", "line": "GK"},
        {"key": "df", "name": "Defender",   "line": "DF"},
        {"key": "mf", "name": "Midfielder", "line": "MF"},
        {"key": "fw", "name": "Forward",    "line": "FW"},
    ]
    for row in data:
        Position.objects.get_or_create(key=row["key"], defaults=row)

def unseed_positions(apps, schema_editor):
    Position = apps.get_model("profiles", "Position")
    Position.objects.filter(key__in=["gk", "df", "mf", "fw"]).delete()

class Migration(migrations.Migration):

    dependencies = [
        ("profiles", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_positions, unseed_positions),
    ]
