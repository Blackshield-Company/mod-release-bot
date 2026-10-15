Title: Company Quartermaster 0.2.1 released
Subreddit: r/skyrimmods

---

**Company Quartermaster 0.2.1** is out.

## What's new

### Fixed
- Brynja looked like a different female bandit each hire because her NPC used the leveled bandit list LCharBanditMeleeNordF as a template with the Traits flag. She is now a unique, non-templated Nord woman with fixed vanilla head parts, hair, iron-and-hide outfit and iron sword.

### Changing Brynja's look
In SSEEdit open `CompanyQuartermaster.esp`, find NPC `CQM_Brynja` (xx000820), change Head Parts, Hair Color, race or outfit (or save it into your own override plugin), then hire her again. For a custom face, export FaceGen in the Creation Kit (Ctrl+F4) or you may get a dark face.

Save-compatible: saves from 0.2.0 and 0.1.0 keep working; no FormIDs changed. A Brynja already hired in an old save keeps her old look until dismissed and hired again.

Early beta: passes Papyrus compile, plugin validation, FOMOD schema, the series compat check and modforge; not playtested in game yet.

## Links

- GitHub release: https://github.com/Blackshield-Company/company-quartermaster/releases/tag/v0.2.1
