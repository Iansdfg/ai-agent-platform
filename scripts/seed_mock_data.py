"""
Seed mock business data for Market Brain Agent.

This script is intentionally idempotent: it uses fixed UUIDs and upserts the
current draft rows, so it can be run repeatedly against an empty or test DB.
It does not modify the RAG vector table; run build_index.py for that.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db import SessionLocal, init_db


MOCK_DRAFTS: List[Dict[str, Any]] = [
    {
        "id": "11111111-1111-4111-8111-111111111111",
        "workspace_id": "default",
        "campaign_id": "q4_petcare",
        "segment_id": "dog_owners",
        "customer_id": None,
        "title": "Q4 Puppy Care Launch Email",
        "content": (
            "Subject: Help your puppy grow strong this season\n\n"
            "Hi there,\n\n"
            "Give your puppy a healthy start with products designed for growth, "
            "comfort, and everyday care. Choose puppy food rich in protein, healthy "
            "fats, and essential nutrients, plus safe accessories tested to meet "
            "industry standards.\n\n"
            "Shop puppy care essentials today."
        ),
        "created_by": "seed",
        "version": 1,
        "event_metadata": {"seed_case": "puppy_care_launch"},
    },
    {
        "id": "22222222-2222-4222-8222-222222222222",
        "workspace_id": "default",
        "campaign_id": "shipping_confidence",
        "segment_id": "recent_buyers",
        "customer_id": None,
        "title": "Shipping Confidence Email",
        "content": (
            "Subject: Your pet essentials are on the way\n\n"
            "Thanks for shopping with us. Standard shipping typically takes 3-7 "
            "business days, and expedited shipping options are available at "
            "checkout. Once your order ships, we will send tracking information "
            "so you can follow every step.\n\n"
            "Track your order when your shipping email arrives."
        ),
        "created_by": "seed",
        "version": 1,
        "event_metadata": {"seed_case": "shipping_update"},
    },
    {
        "id": "33333333-3333-4333-8333-333333333333",
        "workspace_id": "default",
        "campaign_id": "post_purchase_returns",
        "segment_id": "new_customers",
        "customer_id": None,
        "title": "Post-Purchase Return Policy Email",
        "content": (
            "Subject: Need help with your recent order?\n\n"
            "We want you to feel confident after your purchase. Eligible items may "
            "be returned within 30 days of delivery when they are unused, in the "
            "same condition received, and kept in the original packaging. Some "
            "items, including perishable goods, personalized items, gift cards, "
            "and final sale products, are not returnable.\n\n"
            "Questions? Contact support@example.com."
        ),
        "created_by": "seed",
        "version": 1,
        "event_metadata": {"seed_case": "return_policy"},
    },
]


def seed_mock_drafts() -> None:
    init_db()

    with SessionLocal() as db:
        with db.begin():
            for draft in MOCK_DRAFTS:
                draft_id = draft["id"]
                version_id = draft_id.replace("8", "9", 1)
                event_id = draft_id.replace("8", "a", 1)

                db.execute(
                    text("""
                    INSERT INTO drafts (
                        id, workspace_id, campaign_id, segment_id, customer_id,
                        title, content, status, created_by, updated_by, version
                    )
                    VALUES (
                        :id, :workspace_id, :campaign_id, :segment_id, :customer_id,
                        :title, :content, 'draft', :created_by, :created_by, :version
                    )
                    ON CONFLICT (id) DO UPDATE
                    SET workspace_id = EXCLUDED.workspace_id,
                        campaign_id = EXCLUDED.campaign_id,
                        segment_id = EXCLUDED.segment_id,
                        customer_id = EXCLUDED.customer_id,
                        title = EXCLUDED.title,
                        content = EXCLUDED.content,
                        status = EXCLUDED.status,
                        updated_by = EXCLUDED.updated_by,
                        version = EXCLUDED.version,
                        updated_at = NOW()
                    """),
                    draft,
                )

                db.execute(
                    text("""
                    INSERT INTO draft_versions (
                        id, draft_id, version, content, edited_by, edit_instruction
                    )
                    VALUES (
                        :id, :draft_id, :version, :content, :edited_by, :edit_instruction
                    )
                    ON CONFLICT (id) DO UPDATE
                    SET content = EXCLUDED.content,
                        edited_by = EXCLUDED.edited_by,
                        edit_instruction = EXCLUDED.edit_instruction
                    """),
                    {
                        "id": version_id,
                        "draft_id": draft_id,
                        "version": draft["version"],
                        "content": draft["content"],
                        "edited_by": draft["created_by"],
                        "edit_instruction": "seed mock draft",
                    },
                )

                db.execute(
                    text("""
                    INSERT INTO draft_events (
                        id, draft_id, actor_id, event_type, metadata
                    )
                    VALUES (
                        :id, :draft_id, :actor_id, 'draft_seeded', CAST(:metadata AS JSONB)
                    )
                    ON CONFLICT (id) DO UPDATE
                    SET metadata = EXCLUDED.metadata
                    """),
                    {
                        "id": event_id,
                        "draft_id": draft_id,
                        "actor_id": draft["created_by"],
                        "metadata": json.dumps(draft["event_metadata"]),
                    },
                )


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Market Brain mock data.")
    parser.add_argument(
        "--print-ids",
        action="store_true",
        help="Print seeded draft IDs for API/tool testing.",
    )
    args = parser.parse_args()

    seed_mock_drafts()

    print(f"Seeded {len(MOCK_DRAFTS)} Market Brain mock drafts.")
    if args.print_ids:
        for draft in MOCK_DRAFTS:
            print(f"{draft['id']}  {draft['title']}")


if __name__ == "__main__":
    main()
