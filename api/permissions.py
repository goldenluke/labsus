# api/permissions.py

from rest_framework.permissions import BasePermission

from .models import Profile


class HasBphoAccess(BasePermission):
    """
    Libera o acesso apenas a usuários autenticados cujo Profile tem
    has_bpho_access=True. Usado em toda view que consulta a ontologia BPHO
    (PopulationSpace, Chat BPHO, Hospitalização RDF, Vigilância SINAN,
    Registros Vitais, Qualificações CNES), que têm alto custo computacional.
    """

    message = "Este recurso requer acesso à BPHO/PopulationSpace, que ainda não foi liberado para o seu usuário."

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        profile, _ = Profile.objects.get_or_create(user=user)
        return profile.has_bpho_access
