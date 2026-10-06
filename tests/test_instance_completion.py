"""Instance completion preserves identity when Name tags repeat or are absent."""

# Standard Python Libraries
from copy import deepcopy
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

# Third-Party Libraries
import boto3
from botocore.stub import Stubber
import pytest

# cisagov Libraries
from awssh import autocompleter


def instance(identifier, tags):
    """Construct only the fields returned by the EC2 instance collection."""
    return SimpleNamespace(id=identifier, tags=tags)


def named(identifier, name):
    """Make a named instance fixture without accessing AWS."""
    return instance(identifier, [{"Key": "Name", "Value": name}])


@pytest.fixture
def cloud(monkeypatch):
    """Intercept the sole AWS session boundary for every test."""
    ec2 = Mock()
    session = Mock()
    session.resource.return_value = ec2
    session_factory = Mock(return_value=session)
    monkeypatch.setattr(autocompleter.boto3.session, "Session", session_factory)
    with patch.dict(os.environ):
        yield ec2, session_factory


def collect(cloud, records):
    """Call the actual collection helper with fixed resource responses."""
    ec2, _ = cloud
    ec2.instances.filter.return_value = records
    return autocompleter.get_instances(Path("/fixture/unused"), "fixture", "us-east-1")


@pytest.mark.parametrize("reverse", [False, True])
def test_instances_with_the_same_name_remain_distinct(cloud, reverse):
    """Keep both IDs regardless of the order of same-name instances."""
    records = [named("i-0001", "web"), named("i-0002", "web")]
    if reverse:
        records.reverse()
    assert collect(cloud, records) == {("i-0001", "web"), ("i-0002", "web")}


@pytest.mark.parametrize("tags", [None, [], [{"Key": "Owner", "Value": "team"}]])
def test_missing_name_uses_instance_id(cloud, tags):
    """Instances without a Name tag remain usable by their ID."""
    assert collect(cloud, [instance("i-0001", tags)]) == {("i-0001", "i-0001")}


def test_empty_name_retains_its_existing_value(cloud):
    """Preserve an explicitly empty tag rather than inventing a label."""
    assert collect(cloud, [named("i-0001", "")]) == {("i-0001", "")}


def test_unique_names_preserve_collection_filter_and_session_arguments(cloud):
    """Retain running-instance filters and the supplied session location."""
    assert collect(cloud, [named("i-0001", "web"), named("i-0002", "db")]) == {
        ("i-0001", "web"),
        ("i-0002", "db"),
    }
    ec2, factory = cloud
    factory.assert_called_once_with(region_name="us-east-1", profile_name="fixture")
    ec2.instances.filter.assert_called_once_with(
        Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
    )


def test_empty_collection_returns_no_candidates(cloud):
    """An empty instance collection needs no special handling."""
    assert collect(cloud, []) == set()


def test_collection_does_not_rewrite_sdk_resource_objects(cloud):
    """Read SDK resources without adding temporary attributes to them."""
    records = [named("i-0001", "web"), instance("i-0002", None)]
    original = deepcopy([vars(record) for record in records])
    collect(cloud, records)
    assert [vars(record) for record in records] == original


@pytest.mark.parametrize("current", ["web", "i-0001"])
def test_public_completion_only_resolves_an_unambiguous_instance(
    cloud, monkeypatch, current
):
    """Only collapse a completion to an ID when it uniquely matches."""
    ec2, _ = cloud
    ec2.instances.filter.return_value = [named("i-0001", "web"), named("i-0002", "web")]
    monkeypatch.setattr(autocompleter.Path, "is_file", lambda unused: True)
    monkeypatch.setattr(autocompleter, "get_profiles", lambda *args: {"fixture"})
    line = f"awssh --region us-east-1 fixture {current}"
    candidates, word = autocompleter.autocomplete(line, len(line))
    assert word == current
    if current == "web":
        assert candidates == {"web", "i-0001 web", "i-0002 web"}
    else:
        assert candidates == {"i-0001"}


def test_paginated_sdk_responses_preserve_duplicate_names(monkeypatch):
    """Use real EC2 resource objects with stubbed HTTP responses on two pages."""
    ec2 = boto3.resource(
        "ec2",
        region_name="us-east-1",
        aws_access_key_id="testing",
        aws_secret_access_key="testing",
    )
    filters = [{"Name": "instance-state-name", "Values": ["running"]}]
    first = {
        "Reservations": [
            {
                "Instances": [
                    {"InstanceId": "i-0001", "Tags": [{"Key": "Name", "Value": "web"}]}
                ]
            }
        ],
        "NextToken": "next",
    }
    second = {
        "Reservations": [
            {
                "Instances": [
                    {"InstanceId": "i-0002", "Tags": [{"Key": "Name", "Value": "web"}]},
                    {
                        "InstanceId": "i-0003",
                        "Tags": [{"Key": "Owner", "Value": "team"}],
                    },
                ]
            }
        ]
    }
    factory = Mock()
    factory.return_value.resource.return_value = ec2
    monkeypatch.setattr(autocompleter.boto3.session, "Session", factory)
    with Stubber(ec2.meta.client) as stubber, patch.dict(os.environ):
        stubber.add_response("describe_instances", first, {"Filters": filters})
        stubber.add_response(
            "describe_instances", second, {"Filters": filters, "NextToken": "next"}
        )
        actual = autocompleter.get_instances(
            Path("/fixture/unused"), "fixture", "us-east-1"
        )
        assert actual == {("i-0001", "web"), ("i-0002", "web"), ("i-0003", "i-0003")}
        stubber.assert_no_pending_responses()
