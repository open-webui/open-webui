"""
Generate a test markdown document that triggers Bug 3 (tiny orphan fragments).

Settings to use:
  CHUNK_SIZE            = 2048
  CHUNK_MIN_SIZE_TARGET = 1024
  ENABLE_MARKDOWN_HEADER_TEXT_SPLITTER = ON
  TEXT_SPLITTER         = "character"  (default)

The MarkdownHeaderTextSplitter splits on headers, producing one chunk per
section.  The document is crafted so that several tiny heading-only sections
sit between large sections, creating orphan fragments that the old
forward-only merge cannot absorb.
"""

import textwrap


def pad_prose(target_len: int, seed_sentence: str) -> str:
    """Repeat a seed sentence until we hit exactly target_len characters."""
    base = seed_sentence.strip() + " "
    repeated = base * ((target_len // len(base)) + 2)
    return repeated[:target_len]


sections: list[tuple[str, str, int]] = []  # (header, body, body_target_len)

# ── Pattern 1: Large A, tiny B, large C ──────────────────────────────
# A is above min_chunk_size_target (1024) → won't forward-merge
# B is tiny (~35 chars body) → orphaned
# C is large enough that B+C > 2048 → B can't merge forward into C

sections.append((
    "# Chapter 1: Introduction",
    pad_prose(1400, "This is introductory material covering the broad context of the research."),
    1400,
))

sections.append((
    "## 1.1 Scope",
    "Brief scope statement.",  # ~22 chars — tiny orphan
    None,
))

sections.append((
    "## 1.2 Background",
    pad_prose(1950, "Background information provides the historical and technical foundation for this work."),
    1950,
))

# ── Pattern 2: Large D, TWO consecutive tiny E & F, large G ─────────
# Tests that consecutive tiny fragments are each handled.

sections.append((
    "# Chapter 2: Methods",
    pad_prose(1500, "The methodology section describes experimental design and data collection procedures."),
    1500,
))

sections.append((
    "## 2.1 Overview",
    "Short overview.",  # ~15 chars
    None,
))

sections.append((
    "### 2.1.1 Substep",
    "Details.",  # ~8 chars
    None,
))

sections.append((
    "## 2.2 Data Collection",
    pad_prose(1900, "Data was gathered from multiple sources using standardized instruments and protocols."),
    1900,
))

# ── Pattern 3: Large H, tiny I as LAST section ──────────────────────
# Tests backward merge for the very last chunk in the document.

sections.append((
    "# Chapter 3: Results",
    pad_prose(1600, "The results demonstrate statistically significant improvements across all measured dimensions."),
    1600,
))

sections.append((
    "## 3.1 Summary",
    "End.",  # ~4 chars — tiny final orphan
    None,
))


# ── Build the document ───────────────────────────────────────────────
doc_parts = []
print("=" * 65)
print("SECTION SIZES  (header + '\\n\\n' + body)")
print("=" * 65)

for header, body, _ in sections:
    section_text = f"{header}\n\n{body}"
    doc_parts.append(section_text)
    body_len = len(body)
    total_len = len(section_text)
    tag = " *** TINY ***" if body_len < 50 else ""
    print(f"  {header:<30s}  body={body_len:>5d}  total={total_len:>5d}{tag}")

document = "\n\n".join(doc_parts) + "\n"
print(f"\n  Total document length: {len(document)} chars")
print("=" * 65)

# ── Predict chunk behaviour ──────────────────────────────────────────
print("\nEXPECTED CHUNKS AFTER MARKDOWN SPLIT (before merge):")
print("-" * 65)
for i, (header, body, _) in enumerate(sections):
    section_text = f"{header}\n\n{body}"
    # MarkdownHeaderTextSplitter keeps headers in content (strip_headers=False)
    # and splits between sections. Approximate each section as one chunk.
    print(f"  Chunk {i}: {len(section_text):>5d} chars  ← {header}")

print("\nOLD MERGE BEHAVIOUR (forward-only, CHUNK_SIZE=2048, MIN=1024):")
print("-" * 65)
print("  Chunk 0: ~1428 chars  (Ch1 Introduction)")
print("  Chunk 1:   ~35 chars  (1.1 Scope)          *** ORPHAN ***")
print("  Chunk 2: ~1970 chars  (1.2 Background)")
print("  Chunk 3: ~1522 chars  (Ch2 Methods)")
print("  Chunk 4:   ~30 chars  (2.1 Overview)        *** ORPHAN ***")
print("  Chunk 5:   ~27 chars  (2.1.1 Substep)       *** ORPHAN ***")
print("  Chunk 6: ~1924 chars  (2.2 Data Collection)")
print("  Chunk 7: ~1622 chars  (Ch3 Results)")
print("  Chunk 8:   ~19 chars  (3.1 Summary)         *** ORPHAN ***")

print("\nNEW MERGE BEHAVIOUR (forward + backward):")
print("-" * 65)
print("  Chunk 0: ~1463 chars  (Ch1 Introduction + 1.1 Scope)  ← backward merge")
print("  Chunk 1: ~1970 chars  (1.2 Background)")
print("  Chunk 2: ~1554 chars  (Ch2 Methods + 2.1 Overview)    ← backward merge")
print("  Chunk 3:   ~27 chars  (2.1.1 Substep)                 ← merged into Ch2 above")
print("  ...or Ch2+Overview+Substep = ~1583 chars               ← both merged backward")
print("  Chunk 4: ~1924 chars  (2.2 Data Collection)")
print("  Chunk 5: ~1643 chars  (Ch3 Results + 3.1 Summary)     ← backward merge")

print()

# Write the file
output_path = "test_merge_bug3.md"
with open(output_path, "w") as f:
    f.write(document)
print(f"Document written to: {output_path}")
print(f"\nSettings to use:")
print(f"  CHUNK_SIZE                          = 2048")
print(f"  CHUNK_MIN_SIZE_TARGET               = 1024")
print(f"  ENABLE_MARKDOWN_HEADER_TEXT_SPLITTER = ON")
print(f"  TEXT_SPLITTER                        = character (default)")
