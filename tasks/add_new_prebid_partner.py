#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os
import sys
from builtins import input
from pprint import pprint

from colorama import init

import settings
import dfp.associate_line_items_and_creatives
import dfp.create_custom_targeting
import dfp.create_creatives
import dfp.create_line_items
import dfp.create_orders
import dfp.get_advertisers
import dfp.get_ad_units
import dfp.get_custom_targeting
import dfp.get_placements
import dfp.get_users
from dfp.exceptions import (
  BadSettingException,
  MissingSettingException
)
from tasks.price_utils import (
  get_prices_array,
  get_prices_summary_string,
  micro_amount_to_num,
  num_to_str,
)

# Colorama for cross-platform support for colored logging.
# https://github.com/kmjennison/dfp-prebid-setup/issues/9
init()

# Configure logging.
if 'DISABLE_LOGGING' in os.environ and os.environ['DISABLE_LOGGING'] == 'true':
  logging.disable(logging.CRITICAL)
  logging.getLogger('googleads').setLevel(logging.CRITICAL)
  logging.getLogger('oauth2client').setLevel(logging.CRITICAL)
else:
  FORMAT = '%(message)s'
  logging.basicConfig(stream=sys.stdout, level=logging.INFO, format=FORMAT)
  logging.getLogger('googleads').setLevel(logging.ERROR)
  logging.getLogger('oauth2client').setLevel(logging.ERROR)

logger = logging.getLogger(__name__)


def setup_partner(user_email, advertiser_name, order_name, use_placements, placements,
    ad_units, sizes, bidder_code, prices, num_creatives, currency_code):
  """
  Call all necessary DFP tasks for a new Prebid partner setup.
  """

  # Get the user.
  user_id = dfp.get_users.get_user_id_by_email(user_email)

  placement_ids = []
  ad_unit_ids = []

  if use_placements:
    # Get the placement IDs.
    placement_ids = dfp.get_placements.get_placement_ids_by_name(placements)
  else:
    # Get the ad unit IDs.
    ad_unit_ids = dfp.get_ad_units.get_ad_unit_ids_by_name(ad_units)

  # Get (or potentially create) the advertiser.
  advertiser_id = dfp.get_advertisers.get_advertiser_id_by_name(
    advertiser_name)

  # Create the order.
  order_id = dfp.create_orders.create_order(order_name, advertiser_id, user_id)

  # Create creatives.
  creative_configs = dfp.create_creatives.create_duplicate_creative_configs(
      bidder_code, order_name, advertiser_id, num_creatives)
  creative_ids = dfp.create_creatives.create_creatives(creative_configs)

  # Get DFP key IDs for line item targeting.
  hb_bidder_key_id = get_or_create_dfp_targeting_key('hb_bidder')
  hb_pb_key_id = get_or_create_dfp_targeting_key('hb_pb')

  # Instantiate DFP targeting value ID getters for the targeting keys.
  HBBidderValueGetter = DFPValueIdGetter('hb_bidder')
  HBPBValueGetter = DFPValueIdGetter('hb_pb')

  # Create line items.
  line_items_config = create_line_item_configs(prices, order_id,
    use_placements, placement_ids, ad_unit_ids, bidder_code, sizes, hb_bidder_key_id, 
    hb_pb_key_id, currency_code, HBBidderValueGetter, HBPBValueGetter)
  logger.info("Creating line items...")
  line_item_ids = dfp.create_line_items.create_line_items(line_items_config)

  # Associate creatives with line items.
  dfp.associate_line_items_and_creatives.make_licas(line_item_ids,
    creative_ids, size_overrides=sizes)

  logger.info("""

    Done! Please review your order, line items, and creatives to
    make sure they are correct. Then, approve the order in DFP.

    Happy bidding!

  """)

class DFPValueIdGetter(object):
  """
  A class to bulk fetch DFP values by key and then create new values as needed.
  """

  def __init__(self, key_name, *args, **kwargs):
    """
    Args:
      key_name (str): the name of the DFP key
    """
    self.key_name = key_name
    self.key_id = dfp.get_custom_targeting.get_key_id_by_name(key_name)
    self.existing_values = dfp.get_custom_targeting.get_targeting_by_key_name(
      key_name)
    super(DFPValueIdGetter, self).__init__(*args, **kwargs)

  def _get_value_id_from_cache(self, value_name):
    val_id = None
    for value_obj in self.existing_values:
      if value_obj['name'] == value_name:
        val_id = value_obj['id']
        break
    return val_id

  def _create_value_and_return_id(self, value_name):
    return dfp.create_custom_targeting.create_targeting_value(value_name,
      self.key_id)

  def get_value_id(self, value_name):
    """
    Get the DFP custom value ID, or create it if it doesn't exist.

    Args:
      value_name (str): the name of the DFP value
    Returns:
      an integer: the ID of the DFP value
    """
    val_id = self._get_value_id_from_cache(value_name)
    if not val_id:
      val_id = self._create_value_and_return_id(value_name)
    return val_id


def get_or_create_dfp_targeting_key(name):
  """
  Get or create a custom targeting key by name.

  Args:
    name (str)  
  Returns:
    an integer: the ID of the targeting key
  """
  key_id = dfp.get_custom_targeting.get_key_id_by_name(name)
  if key_id is None:
    key_id = dfp.create_custom_targeting.create_targeting_key(name)
  return key_id

def create_line_item_configs(prices, order_id, use_placements, placement_ids, ad_unit_ids,
  bidder_code, sizes, hb_bidder_key_id, hb_pb_key_id, currency_code, HBBidderValueGetter,
  HBPBValueGetter):
  """
  Create a line item config for each price bucket.

  Args:
    prices (array)
    order_id (int)
    use_placements (bool)
    placement_ids (arr)
    ad_unit_ids (arr)
    bidder_code (str)
    hb_bidder_key_id (int)
    hb_pb_key_id (int)
    currency_code (str)
    HBBidderValueGetter (DFPValueIdGetter)
    HBPBValueGetter (DFPValueIdGetter)
  Returns:
    an array of objects: the array of DFP line item configurations
  """

  # The DFP targeting value ID for this `hb_bidder` code.
  hb_bidder_value_id = HBBidderValueGetter.get_value_id(bidder_code)

  line_items_config = []
  for price in prices:

    price_str = num_to_str(micro_amount_to_num(price))

    # Autogenerate the line item name.
    line_item_name = ''
    
    if getattr(settings, 'DFP_LINE_ITEM_PREFIX', None) is not None and settings.DFP_LINE_ITEM_PREFIX != '':
      line_item_name=u'{prefix}{price}'.format(
        prefix=settings.DFP_LINE_ITEM_PREFIX,
        price=price_str
      )
    else:
      line_item_name=u'{bidder_code}: HB ${price}'.format(
        bidder_code=bidder_code,
        price=price_str
      )

    # The DFP targeting value ID for this `hb_pb` price value.
    hb_pb_value_id = HBPBValueGetter.get_value_id(price_str)

    config = dfp.create_line_items.create_line_item_config(
      name=line_item_name,
      order_id=order_id,
      use_placements=use_placements,
      placement_ids=placement_ids,
      ad_unit_ids=ad_unit_ids,
      cpm_micro_amount=price,
      sizes=sizes,
      hb_bidder_key_id=hb_bidder_key_id,
      hb_pb_key_id=hb_pb_key_id,
      hb_bidder_value_id=hb_bidder_value_id,
      hb_pb_value_id=hb_pb_value_id,
      currency_code=currency_code,
    )

    line_items_config.append(config)

  return line_items_config

def check_price_buckets_validity(price_buckets):
  """
  Validate that the price_buckets object contains all required keys and the
  values are the expected types.

  Args:
    price_buckets (object)
  Returns:
    None
  """

  if not isinstance(price_buckets, list):
    raise BadSettingException('The setting "PREBID_PRICE_BUCKETS" '
      'must be a list of price buckets containing "min", "max", and "increment", '
      'and optionally "precision"')

  for price_bucket in price_buckets:
    try:
      pb_min = price_bucket['min']
      pb_max = price_bucket['max']
      pb_increment = price_bucket['increment']
    except KeyError:
      raise BadSettingException('The setting "PREBID_PRICE_BUCKETS" '
        'must contain keys "min", "max", and "increment".')

    if not (isinstance(pb_min, int) or isinstance(pb_min, float)):
      raise BadSettingException('The "min" key in "PREBID_PRICE_BUCKETS" '
        'must be a number.')

    if not (isinstance(pb_max, int) or isinstance(pb_max, float)):
      raise BadSettingException('The "max" key in "PREBID_PRICE_BUCKETS" '
        'must be a number.')

    if not (isinstance(pb_increment, int) or isinstance(pb_increment, float)):
      raise BadSettingException('The "increment" key in "PREBID_PRICE_BUCKETS" '
        'must be a number.')

class color:
   PURPLE = '\033[95m'
   CYAN = '\033[96m'
   DARKCYAN = '\033[36m'
   BLUE = '\033[94m'
   GREEN = '\033[92m'
   YELLOW = '\033[93m'
   RED = '\033[91m'
   BOLD = '\033[1m'
   UNDERLINE = '\033[4m'
   END = '\033[0m'

def main():
  """
  Validate the settings and ask for confirmation from the user. Then,
  start all necessary DFP tasks.
  """

  user_email = getattr(settings, 'DFP_USER_EMAIL_ADDRESS', None)
  if user_email is None:
    raise MissingSettingException('DFP_USER_EMAIL_ADDRESS')
   
  advertiser_name = getattr(settings, 'DFP_ADVERTISER_NAME', None)
  if advertiser_name is None:
    raise MissingSettingException('DFP_ADVERTISER_NAME')

  order_name = getattr(settings, 'DFP_ORDER_NAME', None)
  if order_name is None:
    raise MissingSettingException('DFP_ORDER_NAME')

  use_placements = getattr(settings, 'DFP_USE_PLACEMENT_NAMES', False)

  placements = []
  ad_units = []

  if use_placements:
    placements = getattr(settings, 'DFP_TARGETED_PLACEMENT_NAMES', None)
    if placements is None:
      raise MissingSettingException('DFP_TARGETED_PLACEMENT_NAMES')
    elif len(placements) < 1:
      raise BadSettingException('The setting "DFP_TARGETED_PLACEMENT_NAMES" '
        'must contain at least one DFP placement name.')
  else:
    ad_units = getattr(settings, 'DFP_TARGETED_AD_UNIT_NAMES', None)
    if ad_units is None:
      raise MissingSettingException('DFP_TARGETED_AD_UNIT_NAMES')
    elif len(ad_units) < 1:
      raise BadSettingException('The setting "DFP_TARGETED_AD_UNIT_NAMES" '
        'must contain at least one DFP ad unit name.')

  sizes = getattr(settings, 'DFP_PLACEMENT_SIZES', None)
  if sizes is None:
    raise MissingSettingException('DFP_PLACEMENT_SIZES')
  elif len(sizes) < 1:
    raise BadSettingException('The setting "DFP_PLACEMENT_SIZES" '
      'must contain at least one size object.')

  currency_code = getattr(settings, 'DFP_CURRENCY_CODE', 'USD')

  # How many creatives to attach to each line item. We need at least one
  # creative per ad unit on a page. See:
  # https://github.com/kmjennison/dfp-prebid-setup/issues/13
  num_creatives = (
    getattr(settings, 'DFP_NUM_CREATIVES_PER_LINE_ITEM', None) or
    len(placements)
  )

  bidder_code = getattr(settings, 'PREBID_BIDDER_CODE', None)
  if bidder_code is None:
    raise MissingSettingException('PREBID_BIDDER_CODE')

  price_buckets = getattr(settings, 'PREBID_PRICE_BUCKETS', None)
  if price_buckets is None:
    raise MissingSettingException('PREBID_PRICE_BUCKETS')

  precison = getattr(settings, 'PREBID_DEFAULT_PRICE_PRECISION', 2)

  check_price_buckets_validity(price_buckets)

  prices = get_prices_array(price_buckets)
  prices_summary = get_prices_summary_string(prices, precison)

  targetLogging = u"""

    Going to create {name_start_format}{num_line_items}{format_end} new line items.
      {name_start_format}Order{format_end}: {value_start_format}{order_name}{format_end}
      {name_start_format}Advertiser{format_end}: {value_start_format}{advertiser}{format_end}

    Line items will have targeting:
      {name_start_format}hb_pb{format_end} = {value_start_format}{prices_summary}{format_end}
      {name_start_format}hb_bidder{format_end} = {value_start_format}{bidder_code}{format_end}"""

  if use_placements:
    targetLogging += u"""
      {name_start_format}placements{format_end} = {value_start_format}{placements}{format_end}"""
  else:
    targetLogging += u"""
      {name_start_format}ad_units{format_end} = {value_start_format}{ad_units}{format_end}"""

  targetLogging += "\n"

  logger.info(
    targetLogging.format(
      num_line_items = len(prices),
      order_name=order_name,
      advertiser=advertiser_name,
      user_email=user_email,
      prices_summary=prices_summary,
      bidder_code=bidder_code,
      placements=placements,
      ad_units=ad_units,
      sizes=sizes,
      name_start_format=color.BOLD,
      format_end=color.END,
      value_start_format=color.BLUE,
    ))

  ok = input('Is this correct? (y/n)\n')

  if ok != 'y':
    logger.info('Exiting.')
    return

  setup_partner(
    user_email,
    advertiser_name,
    order_name,
    use_placements,
    placements,
    ad_units,
    sizes,
    bidder_code,
    prices,
    num_creatives,
    currency_code,
  )

if __name__ == '__main__':
  main()
