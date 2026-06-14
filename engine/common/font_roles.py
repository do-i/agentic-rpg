# engine/common/font_roles.py
#
# Shared semantic font-size constants.
#
# Scenes historically hardcoded literal pixel sizes (f.get(13), f.get(14), …)
# for the same role in every file, so there was no single place to tune the
# look. CAPTION is the small descriptive/body tier — item details, status
# persona/backstory, field-menu command subtext, spell descriptions, and the
# small meta labels that sit under headers. Route every such site through this
# constant so one edit keeps the whole game consistent.

CAPTION = 16  # small descriptive/body/meta text (was the scattered 13–14 px tier)
