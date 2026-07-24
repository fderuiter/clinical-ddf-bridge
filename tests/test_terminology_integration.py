import os
import time
from unittest.mock import AsyncMock, patch

from apps.designer import EVSTransportError
from apps.designer.db import (
    MOCK_TERMINOLOGY,
    TerminologyCache,
)


def test_cache_hit_performs_no_external_lookup():
    """Verify that a cache hit performs no external lookup."""
    cache = TerminologyCache(max_size=10, ttl=60.0)
    concept_id = "C999_TEST_HIT"

    mock_concept = {
        "code": "C999_TEST_HIT",
        "decode": "Test Concept Hit",
        "system": "ncit",
        "valid": True,
    }

    with patch.dict(os.environ, {"TERMINOLOGY_OFFLINE": "false"}):
        # Mock the EVS client get_concept method
        with patch(
            "apps.designer.evs_client.NCIEVSClient.get_concept", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_concept

            # Initial request: Cache miss, queries DB/EVS
            val1 = cache.get(concept_id)
            assert val1 == mock_concept
            mock_get.assert_called_once_with(concept_id)

            # Reset mock
            mock_get.reset_mock()

            # Second request: Cache hit, no external lookup
            val2 = cache.get(concept_id)
            assert val2 == mock_concept
            mock_get.assert_not_called()


def test_expired_entry_fallback_on_unreachable_evs():
    """Verify that an expired entry falls back to the stale cached value when EVS is unavailable."""
    # Create cache with very small TTL
    cache = TerminologyCache(max_size=10, ttl=0.01)
    concept_id = "C999_TEST_STALE"

    mock_concept = {
        "code": "C999_TEST_STALE",
        "decode": "Test Concept Stale",
        "system": "ncit",
        "valid": True,
    }

    with patch.dict(os.environ, {"TERMINOLOGY_OFFLINE": "false"}):
        # 1. Populate the cache first
        with patch(
            "apps.designer.evs_client.NCIEVSClient.get_concept", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_concept
            val1 = cache.get(concept_id)
            assert val1 == mock_concept

        # 2. Wait for the TTL to expire
        time.sleep(0.02)

        # 3. DB/EVS is now unreachable (throws EVSTransportError)
        with patch(
            "apps.designer.evs_client.NCIEVSClient.get_concept", new_callable=AsyncMock
        ) as mock_get:
            mock_get.side_effect = EVSTransportError(
                "Connection timeout contacting EVS API"
            )

            # Cache should silently handle the exception and fall back to the expired cached value
            val2 = cache.get(concept_id)
            assert val2 == mock_concept


def test_offline_fallback_resolves_supported_seed_concepts():
    """Verify that offline/configured fallback resolves supported seed concepts."""
    cache = TerminologyCache(max_size=10, ttl=60.0)

    # Enable offline mode via environment variable
    with patch.dict(os.environ, {"TERMINOLOGY_OFFLINE": "true"}):
        with patch(
            "apps.designer.evs_client.NCIEVSClient.get_concept", new_callable=AsyncMock
        ) as mock_get:
            for concept_id, mock_val in MOCK_TERMINOLOGY.items():
                val = cache.get(concept_id)
                # Verify it resolves to seed concept
                assert val is not None
                assert val["code"] == concept_id
                assert val["decode"] == mock_val["decode"]
                # EVS client should not have been called because we are offline
                mock_get.assert_not_called()


def test_existing_cache_consumers_receive_expected_shape():
    """Verify that existing cache consumers continue to receive the expected concept shape."""
    cache = TerminologyCache(max_size=10, ttl=60.0)
    concept_id = "C123"

    with patch.dict(os.environ, {"TERMINOLOGY_OFFLINE": "false"}):
        with patch(
            "apps.designer.evs_client.NCIEVSClient.get_concept", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = {
                "code": "C123",
                "decode": "Treatment Arm",
                "system": "ncit",
                "valid": True,
            }

            val = cache.get(concept_id)
            assert isinstance(val, dict)
            assert "code" in val
            assert "decode" in val
            assert "system" in val
            assert val["code"] == "C123"
            assert val["decode"] == "Treatment Arm"
            assert val["system"] == "ncit"
