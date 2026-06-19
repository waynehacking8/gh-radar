"""gh-radar — a daily digest of trending / shared GitHub tools.

Package layout:
  config     constants, scoring weights, env helpers
  models     the Repo dataclass (typed core model)
  clients    transport: github / firecrawl / claude / http (all degrade to None)
  sources    one src_*() per signal; SOURCES table; enrich()
  scoring    score() + evergreen-noise filter
  state      de-dup memory (seen.json)
  render     zh summaries, Markdown digest, HTML
  email_out  SMTP delivery
  cli        collect -> select -> render -> email -> remember
"""
__version__ = "2.0"
