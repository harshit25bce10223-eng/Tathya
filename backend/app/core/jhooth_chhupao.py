"""Jhooth Chhupao — Adversarial Scenario Catalogue (Spec §20).

Versioned deterministic templates that simulate adversarial injection patterns.
Each scenario is immutable; new scenarios are added via new version, never modifying existing.
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from typing import Any

__all__ = [
    "AdversarialScenario",
    "AdversarialScenarioCatalogue",
    "AdversarialPattern",
]


@dataclass(frozen=True)
class AdversarialScenario:
    """An immutable adversarial scenario template.

    Attributes:
        id: Unique scenario identifier (v4 UUID).
        version: Scenario version string (semantic versioning).
        name: Human-readable scenario name.
        pattern_type: Type of adversarial pattern.
        claim_modification: How the claim is modified.
        evidence_undermine: How evidence is undermined.
        injection_method: Method of claim/evidence injection.
        severity: Severity level (LOW, MEDIUM, HIGH, CRITICAL).
        description: Human-readable description.
        meta: Optional metadata dictionary.
    """

    id: uuid.UUID
    version: str
    name: str
    pattern_type: str
    claim_modification: str
    evidence_undermine: str
    injection_method: str
    severity: str
    description: str
    meta: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for JSON storage."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AdversarialScenario:
        """Deserialize from dictionary."""
        scenario_id = uuid.UUID(data["id"]) if isinstance(data.get("id"), str) else data["id"]
        return cls(
            id=scenario_id,
            version=data["version"],
            name=data["name"],
            pattern_type=data["pattern_type"],
            claim_modification=data["claim_modification"],
            evidence_undermine=data["evidence_undermine"],
            injection_method=data["injection_method"],
            severity=data["severity"],
            description=data["description"],
            meta=data.get("meta"),
        )

    def generates_adversarial_claim(self, base_claim: str) -> str:
        """Generate an adversarial claim from this scenario applied to a base claim."""
        domain = self._extract_domain(base_claim)
        modifiers = {
            "negate": f"Not: {base_claim}",
            "flip_domain": base_claim.replace(domain, self._flip_domain(domain)) if domain else base_claim,
            "add_exception": f"{base_claim} with hidden exception",
            "remove_quantifier": self._remove_quantifier(base_claim),
        }
        return modifiers.get(self.claim_modification, base_claim)

    def _extract_domain(self, claim: str) -> str | None:
        """Extract potential domain/field from claim text."""
        # Simple heuristic: look for capitalized terms that might be domains
        words = claim.split()
        for w in words:
            if w[0].isupper() and len(w) > 3:
                return w
        return None

    def _flip_domain(self, domain: str) -> str:
        """Flip a domain term (e.g., replace with antonym or opposite)."""
        # Simple flip: reverse or substitute
        opposites = {
            "critical": "benign",
            "malicious": "benign",
            "expensive": "affordable",
            "insecure": "secure",
            "vulnerable": "resilient",
        }
        return opposites.get(domain.lower(), domain)

    def _remove_quantifier(self, claim: str) -> str:
        """Remove quantifiers from claim."""
        import re
        return re.sub(r"\b(every|each|all|some|no)\s+", "", claim, count=1, flags=re.IGNORECASE)


@dataclass(frozen=True)
class AdversarialPattern:
    """A reusable adversarial pattern for generating scenarios.

    Attributes:
        pattern_id: Unique pattern identifier.
        name: Pattern name.
        claim_modifications: List of claim modification strategies.
        evidence_undermine_strategies: List of evidence undermining approaches.
        injection_methods: List of injection methods.
        severity_distribution: Distribution of severity levels.
    """

    pattern_id: uuid.UUID
    name: str
    claim_modifications: list[str]
    evidence_undermine_strategies: list[str]
    injection_methods: list[str]
    severity_distribution: list[str]


@dataclass
class AdversarialScenarioCatalogue:
    """Versioned catalogue of adversarial scenarios.

    Scenarios are immutable; new versions are added, never modifying existing entries.
    Provides deterministic lookup by pattern type and severity.
    """

    scenarios: dict[str, AdversarialScenario] = field(default_factory=dict)
    patterns: dict[str, AdversarialPattern] = field(default_factory=dict)
    _version_counter: int = 0

    def add_scenario(self, scenario: AdversarialScenario) -> str:
        """Add a new scenario to the catalogue. Returns the version string."""
        version = f"scenario_v{self._version_counter + 1:03d}"
        self._version_counter += 1
        scenarios = dict(self.scenarios)  # shallow copy for immutability
        scenarios[version] = scenario
        object.__setattr__(self, "scenarios", scenarios)
        return version

    def get_scenario(self, version: str) -> AdversarialScenario | None:
        """Get a scenario by version string."""
        return self.scenarios.get(version)

    def get_scenarios_by_pattern(self, pattern_type: str) -> list[AdversarialScenario]:
        """Get all scenarios matching a pattern type."""
        return [
            s for s in self.scenarios.values()
            if s.pattern_type == pattern_type
        ]

    def get_scenarios_by_severity(self, severity: str) -> list[AdversarialScenario]:
        """Get all scenarios with a given severity level."""
        return [
            s for s in self.scenarios.values()
            if s.severity == severity
        ]

    def generate_adversarial_claim(self, base_claim: str, pattern_type: str | None = None) -> list[tuple[str, str]]:
        """Generate adversarial claims from scenarios matching a pattern type.

        Returns list of (generated_claim, scenario_name) tuples.
        """
        scenarios = (
            self.get_scenarios_by_pattern(pattern_type)
            if pattern_type
            else list(self.scenarios.values())
        )
        results = []
        for scenario in scenarios:
            gen_claim = scenario.generates_adversarial_claim(base_claim)
            results.append((gen_claim, scenario.name))
        return results

    def to_dict(self) -> dict[str, Any]:
        """Serialize catalogue to dictionary."""
        return {
            "scenarios": {v: s.to_dict() for v, s in self.scenarios.items()},
            "patterns": {str(k): p.__dict__ for k, p in self.patterns.items()},
            "version_counter": self._version_counter,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AdversarialScenarioCatalogue:
        """Deserialize catalogue from dictionary."""
        scenarios = {}
        for v, s in data.get("scenarios", {}).items():
            scenarios[v] = AdversarialScenario.from_dict(s)
        patterns = {}
        for k, p in data.get("patterns", {}).items():
            patterns[k] = AdversarialPattern(
                pattern_id=uuid.UUID(k),
                name=p["name"],
                claim_modifications=p["claim_modifications"],
                evidence_undermine_strategies=p["evidence_undermine_strategies"],
                injection_methods=p["injection_methods"],
                severity_distribution=p["severity_distribution"],
            )
        obj = cls(scenarios=scenarios, patterns=patterns)
        obj._version_counter = data.get("version_counter", 0)
        return obj
