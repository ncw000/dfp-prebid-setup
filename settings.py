import os

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
GOOGLEADS_YAML_FILE = os.path.join(ROOT_DIR, 'googleads.yaml')


#########################################################################
# DFP SETTINGS
#########################################################################

# A string describing the order
DFP_ORDER_NAME = 'Nathan Testing36'

# The email of the DFP user who will be the trafficker for
# the created order
DFP_USER_EMAIL_ADDRESS = 'nathanw@zoosk.com'

# The exact name of the DFP advertiser for the created order
DFP_ADVERTISER_NAME = 'Rubicon'

# If True, use Targetd Placement Names. If false, use Ad Unit Names
DFP_USE_PLACEMENT_NAMES = False

# Names of placements the line items should target.
DFP_TARGETED_PLACEMENT_NAMES = ['OnlineNowLeaderboard']

# Names of ad units the line items should target
DFP_TARGETED_AD_UNIT_NAMES = ['TouchSearchAds']

# Sizes of placements. These are used to set line item and creative sizes.
DFP_PLACEMENT_SIZES = [
  {
    'width': '728',
    'height': '90'
  },
]

# Whether we should create the advertiser in DFP if it does not exist.
# If False, the program will exit rather than create an advertiser.
DFP_CREATE_ADVERTISER_IF_DOES_NOT_EXIST = False

# If settings.DFP_ORDER_NAME is the same as an existing order, add the created 
# line items to that order. If False, the program will exit rather than
# modify an existing order.
DFP_USE_EXISTING_ORDER_IF_EXISTS = False

# Optional
# Each line item should have at least as many creatives as the number of 
# ad units you serve on a single page because DFP specifies:
#   "Each of a line item's assigned creatives can only serve once per page,
#    so if you want the same creative to appear more than once per page,
#    copy the creative to associate multiple instances of the same creative."
# https://support.google.com/dfp_sb/answer/82245?hl=en
#
# This will default to the number of placements specified in
# `DFP_TARGETED_PLACEMENT_NAMES`.
DFP_NUM_CREATIVES_PER_LINE_ITEM = 4

# An optional prefix string to use for naming line items. When this value is set
# line items will be named '<prefix>$<price>' instead of '<bidder code> HB $<price>'
DFP_LINE_ITEM_PREFIX = 'Rubicon_DateMix_728x90_ATF_$'

# Optional
# The currency to use in DFP when setting line item CPMs. Defaults to 'USD'.
# DFP_CURRENCY_CODE = 'USD'

#########################################################################
# PREBID SETTINGS
#########################################################################

PREBID_BIDDER_CODE = 'rubicon'

# Price buckets. This should match your Prebid settings for the partner. See:
# http://prebid.org/dev-docs/publisher-api-reference.html#module_pbjs.setPriceGranularity
PREBID_PRICE_BUCKETS = [
{
  'min': 0,
  'max': 3,
  'increment': 0.01
},
{
  'min': 3,
  'max': 8,
  'increment': 0.05
},
{
  'min': 8,
  'max': 20,
  'increment': 0.5
}
]

# The default precision (# of decimals) for the price buckets above. Can be overridden
# by specifying the 'precision' property on a bucket
PREBID_PRICE_PRECISION = 2

#########################################################################

# Try importing local settings, which will take precedence.
try:
    from local_settings import *
except ImportError:
    pass
