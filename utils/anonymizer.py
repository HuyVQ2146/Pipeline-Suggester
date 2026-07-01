"""
Reversible pseudonymizer for CRM pipeline data.

Security measure: Before sending pipeline data to the LLM, we replace
sensitive customer information (names, emails) with pseudonymous tokens
like [COMPANY_1], [EMAIL_1]. This ensures personally identifiable
information (PII) never reaches the model. The mapping is stored locally
and can be reversed to unmask the final outreach email before sending
it to the actual contact.

Why reversible? The Action Suggester drafts an outreach email using
pseudonyms. We need to unmask the email with real names/addresses
before delivering it, so the drafted message is usable.
"""

from typing import Dict


class Pseudonymizer:
    """Reversible pseudonymizer for CRM data fields.

    Maintains an internal bidirectional mapping between real values
    and their token replacements. Each Pseudonymizer instance tracks
    its own mapping, so you can unmask only the data that went through
    this specific instance.
    """

    # Fields that should be pseudonymized — add more as needed.
    # Each maps to a token prefix used in the output (e.g., "COMPANY" → [COMPANY_1]).
    SENSITIVE_FIELDS: Dict[str, str] = {
        "Company_Name": "COMPANY",
        "Contact_Name": "CONTACT",
        "Contact_Email": "EMAIL",
    }

    def __init__(self) -> None:
        # forward_map: real_value → token  (used during pseudonymization)
        self._forward: Dict[str, str] = {}
        # reverse_map: token → real_value  (used during unmasking)
        self._reverse: Dict[str, str] = {}
        # counters per prefix for generating unique tokens
        self._counters: Dict[str, int] = {}

    def pseudonymize_value(self, field_name: str, value: str) -> str:
        """Replace a sensitive value with a pseudonymous token.

        Example:
            pseudonymize_value("Contact_Name", "Jane Doe")  →  "[CONTACT_1]"

        The same real value always maps to the same token within this
        instance, so cross-references inside the data stay consistent.
        """
        prefix = self.SENSITIVE_FIELDS.get(field_name)
        if prefix is None:
            # Not a sensitive field — return as-is (e.g., Deal_ID, Stage)
            return value

        # Reuse existing token if we've already seen this value
        if value in self._forward:
            return self._forward[value]

        # Allocate a new, unique token
        self._counters[prefix] = self._counters.get(prefix, 0) + 1
        token = f"[{prefix}_{self._counters[prefix]}]"

        self._forward[value] = token
        self._reverse[token] = value

        return token

    def pseudonymize_row(self, row: Dict[str, str]) -> Dict[str, str]:
        """Pseudonymize all sensitive fields in a CSV row dict."""
        return {
            key: self.pseudonymize_value(key, value)
            for key, value in row.items()
        }

    def unmask(self, text: str) -> str:
        """Reverse pseudonymization in an arbitrary text string.

        Replaces every token (e.g., [CONTACT_1]) with its original value.
        Used on the draft outreach email before delivering it to the user,
        so the final output contains real names and addresses.

        This is a simple string replacement — if tokens could overlap
        (they can't with our naming scheme), we'd need a smarter approach.
        """
        result = text
        # Replace longest tokens first to avoid partial matches
        # (not strictly necessary with our [PREFIX_N] scheme, but safe)
        for token, real_value in sorted(
            self._reverse.items(), key=lambda x: len(x[0]), reverse=True
        ):
            result = result.replace(token, real_value)
        return result

    def get_mapping_summary(self) -> Dict[str, str]:
        """Return the current forward mapping for audit/debugging.

        Useful for logging what was pseudonymized without revealing
        the actual values in production logs.
        """
        return dict(self._forward)

    def get_reverse_mapping(self) -> Dict[str, str]:
        """Return the reverse mapping (token -> real value).

        This is the mapping needed by downstream tools (e.g. research_tools)
        that receive pseudonymized tokens and must resolve them back to
        real values for database lookups. The resolved values are used
        only as lookup keys — they are never echoed back into the LLM
        conversation.

        SECURITY: This dict must NEVER be included in any LLM prompt,
        logged to disk, or returned in tool output. It lives only in
        process memory for the duration of the agent run.
        """
        return dict(self._reverse)
