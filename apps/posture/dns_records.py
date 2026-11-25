import ipaddress
import re

import dns.exception
import dns.name
import dns.resolver
from django.conf import settings
from django.core.exceptions import ValidationError

LABEL = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?")
RESERVED = {"example", "internal", "invalid", "local", "localhost", "onion", "test", "arpa"}


def normalize_domain(value):
    try:
        name = value.strip().rstrip(".").encode("idna").decode("ascii").lower()
    except UnicodeError as exc:
        raise ValidationError("Enter a public DNS name, such as company.com.") from exc
    labels = name.split(".")
    if len(name) > 227 or len(labels) < 2 or labels[-1] in RESERVED or labels[-1].isdigit() or not all(
        LABEL.fullmatch(label) for label in labels
    ):
        raise ValidationError("Enter a public DNS name, such as company.com.")
    return name


def query_txt(name):
    qname = dns.name.from_text(name + ".")
    resolver = dns.resolver.Resolver(configure=False)
    resolver.nameservers = [str(ipaddress.ip_address(settings.DNS_PUBLIC_RESOLVER))]
    if not ipaddress.ip_address(resolver.nameservers[0]).is_global:
        raise ValueError("DNS_PUBLIC_RESOLVER must be a public address")
    resolver.timeout = 2
    resolver.retry_servfail = False
    try:
        answer = resolver.resolve(qname, "TXT", lifetime=5, search=False, raise_on_no_answer=False)
    except dns.resolver.NXDOMAIN:
        return ()
    except (dns.exception.DNSException, OSError):
        return None
    if answer.canonical_name != qname:
        return None
    records = tuple(b"".join(item.strings) for item in answer)
    return records if len(records) <= 32 and sum(map(len, records)) <= 8192 else None


def summarize(kind, records):
    if records is None:
        return "inconclusive", "The resolver did not return usable exact-name data."
    if kind == "SPF":
        candidates = [record for record in records if re.match(rb"^v=spf1(?: |$)", record, flags=re.IGNORECASE)]
        if not candidates:
            return "missing", "No SPF-tagged TXT record was found at this name."
        if len(candidates) != 1:
            return "needs_review", "More than one SPF-tagged TXT record was found."
        return "present", "One SPF-tagged TXT record was found. Its mechanisms were not evaluated."

    candidates = [record for record in records if re.match(rb"^v=DMARC1(?:[ \t]*;|$)", record)]
    if not candidates:
        return "missing", "No exact-name DMARC record was found. Inheritance is undetermined."
    if len(candidates) != 1:
        return "needs_review", "More than one exact-name DMARC record was found."
    policies = re.findall(rb"(?:^|;)[ \t]*p[ \t]*=[ \t]*([a-z]+)[ \t]*(?=;|$)", candidates[0])
    if len(policies) != 1 or policies[0] not in (b"none", b"quarantine", b"reject"):
        return "needs_review", "The exact-name record has no single recognized policy value."
    policy = policies[0].decode("ascii")
    return "present", f"The exact-name record declares p={policy}. Delivery and enforcement were not evaluated."
