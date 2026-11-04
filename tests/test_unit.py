from __future__ import annotations


def test_import():
    """Test import of jira module."""
    import jira  # noqa: F401


def test_dict2resource_replaces_spaces_in_attribute_names():
    """Field names with spaces become dot-accessible attributes (issue #1865)."""
    from jira.resources import dict2resource

    raw = {
        "fields": {
            "customfield_10004": {
                "steps": [
                    {
                        "index": 1,
                        "fields": {
                            "action": "Step 1",
                            "expected result": "Excepted result 1",
                        },
                    }
                ]
            }
        }
    }
    obj = dict2resource(raw)
    step_fields = obj.fields.customfield_10004.steps[0].fields
    assert step_fields.expected_result == "Excepted result 1"
    assert not hasattr(step_fields, "expected result")


def test_dict2resource_keeps_regular_keys_unchanged():
    """Keys without spaces are passed through verbatim."""
    from jira.resources import dict2resource

    obj = dict2resource({"action": "Step 1", "count": 3})
    assert obj.action == "Step 1"
    assert obj.count == 3
