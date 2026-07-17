import sys
sys.path.insert(0, r'C:\Users\Jignesh\Desktop\bse_portal')
from scripts.db_connect import get_engine
from sqlalchemy import text

engine = get_engine()

with engine.connect() as conn:
    # Find duplicate sector_name groups and their sector_ids
    dup_groups = conn.execute(text("""
        SELECT sector_name, GROUP_CONCAT(sector_id ORDER BY sector_id) as ids
        FROM sectors
        GROUP BY sector_name
        HAVING COUNT(*) > 1
    """)).fetchall()

    print(f"Found {len(dup_groups)} sector names with duplicates.\n")

    total_companies_moved = 0

    for sector_name, ids_str in dup_groups:
        ids = [int(x) for x in ids_str.split(",")]
        canonical_id = ids[0]          # keep the lowest sector_id as canonical
        duplicate_ids = ids[1:]        # everything else gets merged into canonical

        # How many companies currently point to the duplicate ids?
        moved = conn.execute(text("""
            SELECT COUNT(*) FROM companies WHERE sector_id IN :dup_ids
        """), {"dup_ids": tuple(duplicate_ids) if len(duplicate_ids) > 1 else (duplicate_ids[0], duplicate_ids[0])}).fetchone()[0]

        print(f"{sector_name}: canonical={canonical_id}, merging {len(duplicate_ids)} duplicate id(s), moving {moved} companies")
        total_companies_moved += moved

        # Repoint companies from duplicate sector_ids to the canonical one
        conn.execute(text("""
            UPDATE companies SET sector_id = :canonical
            WHERE sector_id IN :dup_ids
        """), {
            "canonical": canonical_id,
            "dup_ids": tuple(duplicate_ids) if len(duplicate_ids) > 1 else (duplicate_ids[0], duplicate_ids[0])
        })

        # Delete the now-empty duplicate sector rows
        conn.execute(text("""
            DELETE FROM sectors WHERE sector_id IN :dup_ids
        """), {"dup_ids": tuple(duplicate_ids) if len(duplicate_ids) > 1 else (duplicate_ids[0], duplicate_ids[0])})

    conn.commit()
    print(f"\nDone. {total_companies_moved} companies repointed, duplicate sector rows removed.")

    # Verify — should print zero rows now
    remaining = conn.execute(text("""
        SELECT sector_name, COUNT(*) FROM sectors GROUP BY sector_name HAVING COUNT(*) > 1
    """)).fetchall()
    print(f"Remaining duplicates: {len(remaining)} (should be 0)")