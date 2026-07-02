# Part 13.2 — Navigation Shell & Persona Control

## Added

- Central shell context provider
- Persona selector
- Scope type selector
- Scope selector
- Period selector
- Compare-to selector
- Active context bar
- Enhanced left navigation
- Sidebar active context summary
- Mobile context drawer placeholder
- Runtime mode status remains in header
- Navigation shell validation script

## Supported Personas

- Firm
- Division
- Region
- Market
- Advisor
- MDW
- DDW

## Supported Scopes

- Firm
- Division
- Region
- Market
- Advisor

## Behavior

Changing the persona automatically changes the default scope:

- Firm → Firm scope
- Division → Division scope
- Region → Region scope
- Market → Market scope
- Advisor → Advisor scope
- MDW → Market scope
- DDW → Division scope

## Validate

```bash
cd frontend
npm run validate:ui
npm run validate:navigation
```
