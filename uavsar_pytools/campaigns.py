"""
SnowEx UAVSAR campaign names and the site codes that start their scene names.
"""

# ASF campaign name -> site code used as the first field of every UAVSAR scene name
CAMPAIGNS = {
    'grmesa': 'Grand Mesa, CO',
    'lowman': 'Lowman, CO',
    'fraser': 'Fraser, CO',
    'irnton': 'Ironton, CO',                    # Senator Beck Basin
    'peeler': 'Peeler Peak, CO',                # East River
    'rockmt': 'Rocky Mountains NP, CO',         # Cameron Pass
    'silver': 'Silver City, ID',                # Reynolds Creek
    'uticam': 'Utica, MT',                      # Central Ag Research Center
    'stlake': 'Salt Lake City, UT',             # Little Cottonwood Canyon
    'alamos': 'Los Alamos, NM',                 # Jemez River
    'dorado': 'Eldorado National Forest, CA',   # American River Basin
    'donner': 'Donner Memorial State Park, CA', # Sagehen Creek
    'sierra': 'Sierra National Forest, CA'      # Lakes Basin
}


def site_code(name):
    """
    Site code for a campaign name or site code, e.g. 'Lowman, CO' -> 'lowman'.
    Unknown names are returned lower cased so other UAVSAR sites still work.
    """
    if name in CAMPAIGNS:
        return name
    for code, campaign in CAMPAIGNS.items():
        if campaign.lower() == name.lower():
            return code
    return name.lower()
