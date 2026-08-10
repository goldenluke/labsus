from django.db import migrations


def criar_profiles_para_usuarios_existentes(apps, schema_editor):
    """Todo usuário já cadastrado no banco começa SEM acesso à BPHO/PopulationSpace."""
    User = apps.get_model('auth', 'User')
    Profile = apps.get_model('api', 'Profile')
    for user in User.objects.all():
        Profile.objects.get_or_create(user=user, defaults={'has_bpho_access': False})


def remover_profiles(apps, schema_editor):
    Profile = apps.get_model('api', 'Profile')
    Profile.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0031_profile'),
    ]

    operations = [
        migrations.RunPython(criar_profiles_para_usuarios_existentes, remover_profiles),
    ]
