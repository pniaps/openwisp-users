import swapper
from django.core.exceptions import ValidationError
from django.db.models import Q
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated

Organization = swapper.load_model('openwisp_users', 'Organization')


class OrgLookup:
    @property
    def organization_lookup(self):
        org_field = getattr(self, 'organization_field', 'organization')
        return f'{org_field}__in'


class FilterByOrganization(OrgLookup):
    """
    Filter queryset based on the access to the organization
    of the associated model. Use on of the sub-classes
    """

    permission_classes = (IsAuthenticated,)

    @property
    def _user_attr(self):
        raise NotImplementedError()

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.is_superuser:
            return qs
        return self.get_organization_queryset(qs)

    def get_organization_queryset(self, qs):
        return qs.filter(
            **{self.organization_lookup: getattr(self.request.user, self._user_attr)}
        )


class FilterByOrganizationMembership(FilterByOrganization):
    """
    Filter queryset by organizations the user is a member of
    """

    _user_attr = 'organizations_dict'


class FilterByOrganizationManaged(FilterByOrganization):
    """
    Filter queryset by organizations managed by user
    """

    _user_attr = 'organizations_managed'


class FilterByOrganizationOwned(FilterByOrganization):
    """
    Filter queryset by organizations owned by user
    """

    _user_attr = 'organizations_owned'


class FilterByParent(OrgLookup):
    """
    Filter queryset based on one of the parent objects
    """

    permission_classes = (IsAuthenticated,)

    @property
    def _user_attr(self):
        raise NotImplementedError()

    def get_queryset(self):
        qs = super().get_queryset()
        self.assert_parent_exists()
        return qs

    def assert_parent_exists(self):
        parent_queryset = self.get_parent_queryset()
        if not self.request.user.is_superuser:
            parent_queryset = self.get_organization_queryset(parent_queryset)
        try:
            assert parent_queryset.exists()
        except (AssertionError, ValidationError):
            raise NotFound()

    def get_organization_queryset(self, qs):
        lookup = {self.organization_lookup: getattr(self.request.user, self._user_attr)}
        return qs.filter(**lookup)

    def get_parent_queryset(self):
        raise NotImplementedError()


class FilterByParentMembership(FilterByParent):
    """
    Filter queryset based on parent organization membership
    """

    _user_attr = 'organizations_dict'


class FilterByParentManaged(FilterByParent):
    """
    Filter queryset based on parent organizations managed by user
    """

    _user_attr = 'organizations_managed'


class FilterByParentOwned(FilterByParent):
    """
    Filter queryset based on parent organizations owned by user
    """

    _user_attr = 'organizations_owned'


class FilterSerializerByOrganization(OrgLookup):
    """
    Filter the options in browsable API for serializers
    """

    include_shared = False

    @property
    def _user_attr(self):
        raise NotImplementedError()

    def filter_fields(self):
        user = self.context['request'].user
        if user.is_superuser:
            return
        organization_filter = getattr(user, self._user_attr)
        for field in self.fields:
            if field == 'organization':
                self.fields[field].allow_null = False
                self.fields[field].queryset = self.fields[field].queryset.filter(
                    pk__in=organization_filter
                )
                continue
            try:
                conditions = Q(**{self.organization_lookup: organization_filter})
                if self.include_shared:
                    conditions |= Q(organization__isnull=True)
                self.fields[field].queryset = self.fields[field].queryset.filter(
                    conditions
                )
            except AttributeError:
                pass

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.filter_fields()


class FilterSerializerByOrgMembership(FilterSerializerByOrganization):
    """
    Filter serializer by organizations the user is member of
    """

    _user_attr = 'organizations_dict'


class FilterSerializerByOrgManaged(FilterSerializerByOrganization):
    """
    Filter serializer by organizations managed by user
    """

    _user_attr = 'organizations_managed'


class FilterSerializerByOrgOwned(FilterSerializerByOrganization):
    """
    Filter serializer by organizations owned by user
    """

    _user_attr = 'organizations_owned'
