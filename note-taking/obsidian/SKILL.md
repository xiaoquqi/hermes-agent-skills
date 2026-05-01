---
name: obsidian
description: Read, search, and create notes in the Obsidian vault.
---

# Obsidian Vault

**Location:** The vault path is stored in Obsidian's config at `~/Library/Application Support/obsidian/obsidian.json`. Look for the `path` field in the vaults object.

**iCloud vaults:** On macOS, Obsidian stores iCloud vaults at:
```
/Users/ray/Library/Mobile Documents/iCloud~md~obsidian/Documents/<VaultName>
```

For Ray's vault: `/Users/ray/Library/Mobile Documents/iCloud~md~obsidian/Documents/Ray`

Note: Vault paths may contain spaces - always quote them.

**On macOS with iCloud:** Obsidian vaults are typically stored locally in `~/Documents/`, NOT in the iCloud container (`~/Library/Mobile Documents/com~apple~CloudDocs/`). If a vault appears missing from iCloud, check `~/Documents/Obsidian Vault/` first. The presence of a backup `.zip` in iCloud does not mean the vault itself is stored there.

## Read a note

```bash
VAULT="${OBSIDIAN_VAULT_PATH:-$HOME/Documents/Obsidian Vault}"
cat "$VAULT/Note Name.md"
```

## List notes

```bash
VAULT="${OBSIDIAN_VAULT_PATH:-$HOME/Documents/Obsidian Vault}"

# All notes
find "$VAULT" -name "*.md" -type f

# In a specific folder
ls "$VAULT/Subfolder/"
```

## Search

```bash
VAULT="${OBSIDIAN_VAULT_PATH:-$HOME/Documents/Obsidian Vault}"

# By filename
find "$VAULT" -name "*.md" -iname "*keyword*"

# By content
grep -rli "keyword" "$VAULT" --include="*.md"
```

## Create a note

```bash
VAULT="${OBSIDIAN_VAULT_PATH:-$HOME/Documents/Obsidian Vault}"
cat > "$VAULT/New Note.md" << 'ENDNOTE'
# Title

Content here.
ENDNOTE
```

## Append to a note

```bash
VAULT="${OBSIDIAN_VAULT_PATH:-$HOME/Documents/Obsidian Vault}"
echo "
New content here." >> "$VAULT/Existing Note.md"
```

## Wikilinks

Obsidian links notes with `[[Note Name]]` syntax. When creating notes, use these to link related content.
