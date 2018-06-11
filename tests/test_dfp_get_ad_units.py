
from unittest import TestCase
from mock import MagicMock, Mock, patch

import dfp.get_ad_units
from dfp.exceptions import (
  BadSettingException,
  DFPObjectNotFound,
  MissingSettingException
)


@patch('googleads.dfp.DfpClient.LoadFromStorage')
class DFPGetAdUnitTests(TestCase):

  def test_get_ad_unit_by_name_call(self, mock_dfp_client):
    """
    Ensure we make the correct call to DFP when getting an ad unit
    by name.
    """
    mock_dfp_client.return_value = MagicMock()
    ad_unit_name = 'My Nice Placement'

    # Response from DFP.
    (mock_dfp_client.return_value
      .GetService.return_value
      .getAdUnitsByStatement) = MagicMock(
        return_value={
          'totalResultSetSize': 1,
          'startIndex': 0,
          'results': [{
            'targetingDescription': None,
            'targetingSiteName': None,
            'targetingAdLocation': None,
            'id': 22334455,
            'name': ad_unit_name,
            'description': None,
            'adUnitCode': "111222333444555666",
            'status': "ACTIVE",
            'isAdSenseTargetingEnabled': False,
            'adSenseTargetingLocale': "und",
            'targetedAdUnitIds': ['123456789'],
            'lastModifiedDateTime': {},
          }]
        }
    )

    dfp.get_ad_units.get_ad_unit_by_name(ad_unit_name)

    # Expected argument to use in call to DFP.
    expected_statement = {
      'query': 'WHERE name = :name LIMIT 500 OFFSET 0',
      'values': [{
        'value': {
          'value': ad_unit_name,
          'xsi_type': 'TextValue'
          },
          'key': 'name'
        }]
    }

    (mock_dfp_client.return_value
      .GetService.return_value
      .getAdUnitsByStatement.assert_called_once_with(expected_statement)
      )

  def test_get_ad_unit_by_name(self, mock_dfp_client):
    """
    Ensure we return the ad unit when it's fetched successfully.
    """
    mock_dfp_client.return_value = MagicMock()
    ad_unit_name = 'My Neat Placement'

    # Response from DFP.
    (mock_dfp_client.return_value
      .GetService.return_value
      .getAdUnitsByStatement) = MagicMock(
        return_value={
          'totalResultSetSize': 1,
          'startIndex': 0,
          'results': [{
            'targetingDescription': None,
            'targetingSiteName': None,
            'targetingAdLocation': None,
            'id': 22334455,
            'name': ad_unit_name,
            'description': None,
            'adUnitCode': "111222333444555666",
            'status': "ACTIVE",
            'isAdSenseTargetingEnabled': False,
            'adSenseTargetingLocale': "und",
            'targetedAdUnitIds': ['123456789'],
            'lastModifiedDateTime': {},
          }]
        }
    )

    ad_unit = dfp.get_ad_units.get_ad_unit_by_name(ad_unit_name)
    self.assertEqual(ad_unit['id'], 22334455)

  def test_get_no_ad_unit_by_name(self, mock_dfp_client):
    """
    Ensure we throw an exception when the ad unit doesn't exist.
    """
    mock_dfp_client.return_value = MagicMock()

    # Response from DFP.
    (mock_dfp_client.return_value
      .GetService.return_value
      .getAdUnitsByStatement) = MagicMock(
        return_value={
          'totalResultSetSize': 0,
          'startIndex': 0,
      }
    )

    with self.assertRaises(DFPObjectNotFound):
      ad_unit = dfp.get_ad_units.get_ad_unit_by_name(
        'Not an Existing Placement')

  @patch('dfp.get_ad_units.get_ad_unit_by_name')
  def test_get_ad_unit_ids_by_name(self, mock_get_ad_unit_by_name, 
    mock_dfp_client):
    """
    Ensures we return ad unit IDs.
    """

    # Fake returned ad unit. Return a different one each time
    # it is called.
    mock_get_ad_unit_by_name.side_effect = [
      {
        'targetingDescription': None,
        'targetingSiteName': None,
        'targetingAdLocation': None,
        'id': 9988776655,
        'name': 'Placement One.',
        'description': None,
        'adUnitCode': "111222333444555666",
        'status': "ACTIVE",
        'isAdSenseTargetingEnabled': False,
        'adSenseTargetingLocale': "und",
        'targetedAdUnitIds': ['123456789'],
        'lastModifiedDateTime': {},
      },
      {
        'targetingDescription': None,
        'targetingSiteName': None,
        'targetingAdLocation': None,
        'id': 13571357,
        'name': 'Placement Two.',
        'description': None,
        'adUnitCode': "111222333444555666",
        'status': "ACTIVE",
        'isAdSenseTargetingEnabled': False,
        'adSenseTargetingLocale': "und",
        'targetedAdUnitIds': ['123456789'],
        'lastModifiedDateTime': {},
      }
    ]
    ad_unit_ids = dfp.get_ad_units.get_ad_unit_ids_by_name(
      ['Placement One.', 'Placement Two.'])
    self.assertEqual(ad_unit_ids, [9988776655, 13571357])

  @patch.multiple('settings',
    DFP_TARGETED_AD_UNIT_NAMES=['My Placement!', 'Another placment'])
  @patch('dfp.get_ad_units.get_ad_unit_ids_by_name')
  def test_settings_ad_units(self, mock_get_ad_unit_ids_by_names,
    mock_dfp_client):
    """
    Ensures we use the ad unit names from the settings file.
    """
    
    # Fake returned ad unit IDs
    mock_get_ad_unit_ids_by_names.return_value = [223344556, 123456789]
    dfp.get_ad_units.main()
    mock_get_ad_unit_ids_by_names.assert_called_once_with(
      ['My Placement!', 'Another placment'])

  @patch.multiple('settings', DFP_TARGETED_AD_UNIT_NAMES=None)
  def test_create_orders_missing_ad_units_setting(self, mock_dfp_client):
    """
    Ensures we raise an exception if the ad_units setting
    does not exist.
    """
    
    with self.assertRaises(MissingSettingException):
      dfp.get_ad_units.main()

  @patch.multiple('settings', DFP_TARGETED_AD_UNIT_NAMES=[])
  def test_create_orders_bad_ad_units_setting(self, mock_dfp_client):
    """
    Ensures we raise an exception if the ad_units setting
    does not contain any ad unit names.
    """
    
    with self.assertRaises(BadSettingException):
      dfp.get_ad_units.main()
