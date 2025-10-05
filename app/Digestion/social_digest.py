# app/Digestion/social_digest.py

from typing import Any, Dict


class SocialDigest:
    """Collect token visibility & community presence metrics."""

    @staticmethod
    def digest(enriched_token: Dict[str, Any]) -> Dict[str, Any]:
        """Extract social presence data and compute derived fields for AI."""
        try:
            info = enriched_token.get("info", {}) or {}
            socials = info.get("socials", [])
            websites = info.get("websites", [])

            # Normalize socials/websites into list form
            if isinstance(socials, dict):
                socials = [
                    {"platform": k, "url": v}
                    for k, v in socials.items() if v
                ]

            if isinstance(websites, dict):
                websites = [v for v in websites.values() if v]

            has_twitter = False
            twitter_url = None
            has_discord = False
            has_telegram = False

            for social in socials:
                if isinstance(social, dict):
                    platform = str(social.get("platform", "")).lower()
                    url = str(social.get("url", ""))
                elif isinstance(social, str):
                    platform = social.lower()
                    url = social
                else:
                    continue

                # Detect Twitter/X link — store full URL
                if "twitter" in platform or "x.com" in url.lower():
                    has_twitter = True
                    twitter_url = url.strip()

                elif "discord" in platform or "discord" in url.lower():
                    has_discord = True

                elif "telegram" in platform or "t.me" in url.lower():
                    has_telegram = True

            has_website = bool(websites)
            has_header_image = bool(info.get("logoURI"))

            social_presence_score = sum([
                has_website,
                has_twitter,
                has_header_image,
                has_discord,
                has_telegram,
            ])

            verified_community = False  # Placeholder for API-based verification

            return {
                "has_twitter": has_twitter,
                "twitter_url": twitter_url,  # <── now stores the full link
                "has_website": has_website,
                "has_header_image": has_header_image,
                "has_discord": has_discord,
                "has_telegram": has_telegram,
                "social_presence_score": social_presence_score,
                "verified_community": verified_community,
            }

        except Exception as e:
            return {
                "has_twitter": False,
                "twitter_url": None,
                "has_website": False,
                "has_header_image": False,
                "has_discord": False,
                "has_telegram": False,
                "social_presence_score": 0,
                "verified_community": False,
                "_error": str(e),
            }
