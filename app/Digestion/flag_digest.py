# app/Digestion/flag_digest.py

from typing import Any, Dict, List


class FlagDigest:
    """Gather security/rug/risk indicators safely."""

    @staticmethod
    def digest(enriched_token: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract security flags and compute derived fields for AI.

        Args:
            enriched_token: Full enriched token data from all sources

        Returns:
            Dict containing security and risk flags
        """
        try:
            rugcheck = enriched_token.get("rugcheck", {}) or {}

            # Basic rug status
            rugged = bool(rugcheck.get("rugged") or False)

            # Authority flags
            token_meta = rugcheck.get("tokenMeta") or {}
            has_freeze_authority = bool(token_meta.get("freezeAuthority") or False)
            has_mint_authority = bool(token_meta.get("mintAuthority") or False)

            # Risk flags
            risks = rugcheck.get("risks") or []
            risk_flags: List[str] = []

            if isinstance(risks, list):
                for risk in risks:
                    if isinstance(risk, dict):
                        r_type = str(risk.get("type") or "").strip()
                        if r_type:
                            risk_flags.append(r_type)
                    elif isinstance(risk, str):
                        risk_flags.append(risk.strip())

            # On-chain verification
            verified_on_chain = bool(enriched_token.get("on_chain_verified") or False)

            # Derived AI fields
            revocation_risk_score = 1.0 if has_mint_authority else 0.0

            rug_likelihood_flag = bool(
                rugged or
                len(risk_flags) > 2 or
                has_freeze_authority or
                has_mint_authority
            )

            # Trust score (bounded between 0–1)
            trust_score = 1.0 - sum([
                float(rugged),
                float(has_freeze_authority),
                float(has_mint_authority),
                min(1.0, len(risk_flags) / 5.0)
            ])
            trust_score = max(0.0, min(1.0, trust_score))

            # Additional security metadata
            has_verified_creator = bool(rugcheck.get("verifiedCreator") or False)
            has_kyc = bool(rugcheck.get("kycVerified") or False)

            return {
                "rugged": rugged,
                "has_freeze_authority": has_freeze_authority,
                "has_mint_authority": has_mint_authority,
                "risk_flags": risk_flags,
                "verified_on_chain": verified_on_chain,
                "revocation_risk_score": revocation_risk_score,
                "rug_likelihood_flag": rug_likelihood_flag,
                "trust_score": trust_score,
                "has_verified_creator": has_verified_creator,
                "has_kyc": has_kyc,
            }

        except Exception as e:
            return {
                "rugged": False,
                "has_freeze_authority": False,
                "has_mint_authority": False,
                "risk_flags": [],
                "verified_on_chain": False,
                "revocation_risk_score": 0.0,
                "rug_likelihood_flag": False,
                "trust_score": 0.0,
                "has_verified_creator": False,
                "has_kyc": False,
                "_error": str(e),
            }
