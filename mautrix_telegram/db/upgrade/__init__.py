from mautrix.util.async_db import UpgradeTable

upgrade_table = UpgradeTable()

from . import (  # isort:skip
    v01_initial_revision,
    v02_sponsored_events,
    v03_reactions,
    v04_disappearing_messages,
    v05_channel_ghosts,
    v06_puppet_avatar_url,
    v07_puppet_phone_number,
    v08_portal_first_event,
    v09_puppet_username_index,
    v10_more_backfill_fields,
    v11_backfill_queue,
    v12_message_sender,
    v13_multiple_reactions,
    v14_puppet_custom_mxid_index,
    # Note: In upstream, message_find_recent is a v17
    # and backfill_anchor_id and backfill_type are v15 and v16 respectively.
    # We shift them around a little since we introduced message_find_recent earlier.
    v15_message_find_recent,
    v16_backfill_anchor_id,
    v17_backfill_type,
    v18_puppet_contact_info_set,
)
