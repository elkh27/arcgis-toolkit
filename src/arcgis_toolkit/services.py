"""Find hosted feature services in the signed-in user's organization."""


def org_feature_services(gis, title: str | None = None) -> list:
    """All feature services in the organization, optionally only those with an exact title."""
    org_id = gis.users.me.orgId
    items = gis.content.search(query=f"orgid:{org_id}", item_type="Feature Service", max_items=10_000)
    if title:
        items = [i for i in items if i.title == title]
    return items


def find_service(gis, title: str):
    items = org_feature_services(gis, title)
    if not items:
        raise LookupError(f"No feature service titled {title!r} in this organization")
    return items[0]