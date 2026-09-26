"""Product photo URL rules, shared by every path that writes image_url
(Rakuten/Yahoo price fetch, discovery, CSV import, admin edits, the
backfill in app/image_backfill.py).

Mirrors frontend/lib/imageUrl.ts: the frontend shows the NO IMAGE
placeholder for anything this module rejects, so a product whose stored
value is rejected here is one that "needs an image" - and the daily price
fetch is allowed to fill it in from the listing it matched.
"""

import urllib.parse

import httpx

# Hosts that are never a real product photo: the sample CSV's example.com
# URLs, and local-dev hosts that can't be reached from a visitor's browser.
PLACEHOLDER_HOSTS = {"example.com", "example.org", "example.net", "localhost", "127.0.0.1", "0.0.0.0"}

REACHABILITY_TIMEOUT_SECONDS = 5.0


def normalize_image_url(raw: str | None) -> str | None:
    """A loadable https URL, or None.

    - None / "" / whitespace -> None
    - "http://..." -> "https://..." (par-gear.com is https; Rakuten's and
      Yahoo's image CDNs both serve https)
    - "//host/..." -> "https://host/..."
    - placeholder / local hosts, other schemes, relative paths -> None
    """
    if not isinstance(raw, str):
        return None
    value = raw.strip()
    if not value:
        return None
    if value.startswith("//"):
        value = "https:" + value
    elif value[:7].lower() == "http://":
        value = "https://" + value[7:]

    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        return None
    host = parsed.hostname.lower()
    if host in PLACEHOLDER_HOSTS or any(host.endswith("." + h) for h in PLACEHOLDER_HOSTS):
        return None
    return urllib.parse.urlunsplit(("https", parsed.netloc, parsed.path, parsed.query, parsed.fragment))


def needs_image(image_url: str | None) -> bool:
    """True when the stored value can't be shown as a photo (so the site
    renders NO IMAGE) - the only case an automatic fill may overwrite it.
    A valid URL an admin set is never replaced automatically."""
    return normalize_image_url(image_url) is None


def is_definitely_broken(url: str, timeout: float = REACHABILITY_TIMEOUT_SECONDS) -> bool:
    """True only when the image server gives a definitive answer that the
    photo isn't there (404/410, or a 200 that isn't an image). A timeout, a
    connection error, a 403 or a 5xx is NOT treated as broken - a transient
    outage must never wipe a good photo."""
    try:
        with httpx.stream("GET", url, timeout=timeout, follow_redirects=True) as response:
            if response.status_code in (404, 410):
                return True
            if response.status_code >= 400:
                # 403 etc. can be a CDN refusing a script's user agent while
                # browsers load the photo fine - not proof it's gone.
                return False
            content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
            return bool(content_type) and not content_type.startswith("image/")
    except httpx.HTTPError:
        return False
