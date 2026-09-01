# Paying Down Debt — Middle

## Goal

Choose the smallest repayment strategy that reduces future cost safely.

## Options

- Continuous cleanup for tiny, local improvements.
- Fix-on-touch for code changed by a feature.
- Dedicated work for a known, contained hotspot.
- Incremental replacement for a module with high risk.

## Safety net

- Add characterization tests when the intended behavior is unknown.
- Separate tidyings from behavior changes in commits and reviews.
- Measure whether the next change became faster or safer.

## Avoid

- Big-bang rewrites.
- Refactoring without tests, observability, or rollback.
- Declaring victory because code looks newer.
