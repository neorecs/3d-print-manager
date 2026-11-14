"""What each sales channel accepts and how the app works with it.

mode "api": the app publishes, syncs stock and imports orders itself.
mode "hulpmodus": the app prepares the complete listing (text per field, the
right photos) and the seller places it by hand; orders are entered with one form.

Only limits that the channel documents are enforced; everything else is advice.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ChannelProfile:
    key: str
    label: str
    mode: str
    title_max: int | None = None
    tags_max_count: int | None = None
    tag_max_length: int | None = None
    photos_max: int | None = None
    requires_original_photo: bool = False
    requires_ean: bool = False
    requires_shipping_profile: bool = False
    one_listing_per_item: bool = False
    notes: tuple[str, ...] = field(default_factory=tuple)


PROFILES: dict[str, ChannelProfile] = {
    "etsy": ChannelProfile(
        key="etsy", label="Etsy", mode="api", title_max=140, tags_max_count=13, tag_max_length=20,
        requires_original_photo=True, requires_shipping_profile=True,
        notes=("Minstens één onbewerkte foto van het echte product tegen een echte achtergrond.",
               "Geen volledig geautomatiseerde vermeldingen: controleer elke vermelding zelf."),
    ),
    "shopify": ChannelProfile(key="shopify", label="Shopify", mode="api"),
    "bol": ChannelProfile(
        key="bol", label="bol", mode="api", requires_ean=True,
        notes=("Elk aanbod hoort bij een EAN-code; content wordt gedeeld met andere verkopers van dezelfde EAN.",),
    ),
    "marktplaats": ChannelProfile(
        key="marktplaats", label="Marktplaats", mode="hulpmodus", photos_max=24,
        notes=("Automatisch plaatsen mag alleen met toestemming van Marktplaats (API-partner); tot die tijd hulpmodus.",),
    ),
    "vinted": ChannelProfile(
        key="vinted", label="Vinted", mode="hulpmodus", photos_max=20, one_listing_per_item=True,
        notes=("Vinted richt zich op tweedehands mode; controleer of nieuwe 3D-prints passen.",
               "Identieke artikelen mogen niet twee keer worden geplaatst; gebruik eigen foto's."),
    ),
}

GENERIC = ChannelProfile(key="overig", label="Overig kanaal", mode="hulpmodus")


def channel_profile(platform_type: str | None) -> ChannelProfile:
    return PROFILES.get((platform_type or "").strip().lower(), GENERIC)


def is_assisted(platform_type: str | None) -> bool:
    return channel_profile(platform_type).mode == "hulpmodus"


def profile_dict(profile: ChannelProfile) -> dict:
    return {
        "key": profile.key, "label": profile.label, "mode": profile.mode,
        "title_max": profile.title_max, "tags_max_count": profile.tags_max_count, "tag_max_length": profile.tag_max_length,
        "photos_max": profile.photos_max, "requires_original_photo": profile.requires_original_photo,
        "requires_ean": profile.requires_ean, "requires_shipping_profile": profile.requires_shipping_profile,
        "one_listing_per_item": profile.one_listing_per_item, "notes": list(profile.notes),
    }


def listing_issues(profile: ChannelProfile, channel_name: str, title: str | None, tags: list[str], photo_count: int,
                   original_photo_count: int | None = None) -> list[str]:
    """Errors against the channel's documented limits."""
    errors = []
    if profile.title_max and title and len(title) > profile.title_max:
        errors.append(f"{channel_name}: {profile.label}-titel mag maximaal {profile.title_max} tekens zijn.")
    if profile.tags_max_count and len(tags) > profile.tags_max_count:
        errors.append(f"{channel_name}: {profile.label} ondersteunt maximaal {profile.tags_max_count} tags.")
    if profile.tag_max_length:
        long_tags = [tag for tag in tags if len(tag) > profile.tag_max_length]
        if long_tags:
            errors.append(f"{channel_name}: {profile.label}-tags mogen maximaal {profile.tag_max_length} tekens zijn: {', '.join(long_tags)}.")
    if profile.photos_max and photo_count > profile.photos_max:
        errors.append(f"{channel_name}: {profile.label} accepteert maximaal {profile.photos_max} foto's.")
    if profile.requires_original_photo and original_photo_count == 0 and photo_count > 0:
        errors.append(f"{channel_name}: {profile.label} vraagt minstens één onbewerkte foto van het echte product.")
    return errors
