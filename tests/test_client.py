import getpass

import pytest

import jira.client
from jira.exceptions import JIRAError
from tests.conftest import JiraTestManager, get_unique_project_name

# from tenacity import retry
# from tenacity import wait_incrementing


@pytest.fixture()
def prep():
    pass


@pytest.fixture(scope="module")
def test_manager() -> JiraTestManager:
    return JiraTestManager()


@pytest.fixture()
def cl_admin(test_manager: JiraTestManager) -> jira.client.JIRA:
    return test_manager.jira_admin


@pytest.fixture()
def cl_normal(test_manager: JiraTestManager) -> jira.client.JIRA:
    return test_manager.jira_normal


@pytest.fixture(scope="function")
def slug(request, cl_admin):
    def remove_by_slug():
        try:
            cl_admin.delete_project(slug)
        except (ValueError, JIRAError):
            # Some tests have project already removed, so we stay silent
            pass

    slug = get_unique_project_name()

    project_name = f"Test user={getpass.getuser()} key={slug} A"

    try:
        proj = cl_admin.project(slug)
    except JIRAError:
        proj = cl_admin.create_project(slug, project_name)
    assert proj

    request.addfinalizer(remove_by_slug)

    return slug


@pytest.fixture()
def no_fields(monkeypatch):
    """When we want to test the __init__ method of the jira.client.JIRA
    we don't need any external calls to get the fields.

    We don't need the features of a MagicMock, hence we don't use it here.
    """
    monkeypatch.setattr(jira.client.JIRA, "fields", lambda *args, **kwargs: [])


def test_delete_project(cl_admin, cl_normal, slug):

    assert cl_admin.delete_project(slug)


def test_delete_inexistent_project(cl_admin):
    slug = "abogus123"
    with pytest.raises(JIRAError) as ex:
        assert cl_admin.delete_project(slug)

    assert "No project could be found with key" in str(
        ex.value
    ) or 'Parameter pid="%s" is not a Project, projectID or slug' % slug in str(
        ex.value
    )


def test_templates(cl_admin):
    templates = set(cl_admin.templates())
    expected_templates = set(
        filter(
            None,
            """
Basic software development
Kanban software development
Process management
Project management
Scrum software development
Task management
""".split(
                "\n"
            ),
        )
    )

    assert templates == expected_templates


def test_result_list():
    iterable = [2, 3]
    startAt = 0
    maxResults = 50
    total = 2

    results = jira.client.ResultList(iterable, startAt, maxResults, total)

    for idx, result in enumerate(results):
        assert results[idx] == iterable[idx]

    assert next(results) == iterable[0]
    assert next(results) == iterable[1]

    with pytest.raises(StopIteration):
        next(results)


def test_result_list_if_empty():
    results = jira.client.ResultList()

    for r in results:
        raise AssertionError("`results` should be empty")

    with pytest.raises(StopIteration):
        next(results)


@pytest.mark.parametrize(
    "options_arg",
    [
        {"headers": {"Content-Type": "application/json;charset=UTF-8"}},
        {"headers": {"random-header": "nice random"}},
    ],
    ids=["overwrite", "new"],
)
def test_headers_unclobbered_update(options_arg, no_fields):

    assert "headers" in options_arg, "test case options must contain headers"

    # GIVEN: the headers and the expected value
    header_to_check: str = list(options_arg["headers"].keys())[0]
    expected_header_value: str = options_arg["headers"][header_to_check]

    invariant_header_name: str = "X-Atlassian-Token"
    invariant_header_value: str = jira.client.JIRA.DEFAULT_OPTIONS["headers"][
        invariant_header_name
    ]

    # We arbitrarily chose a header to check it remains unchanged/unclobbered
    # so should not be overwritten by a test case
    assert (
        invariant_header_name not in options_arg["headers"]
    ), f"{invariant_header_name} is checked as not being overwritten in this test"

    # WHEN: we initialise the JIRA class and get the headers
    jira_client = jira.client.JIRA(
        server="https://jira.atlasian.com",
        get_server_info=False,
        validate=False,
        options=options_arg,
    )

    session_headers = jira_client._session.headers

    # THEN: we have set the right headers and not affect the other headers' defaults
    assert session_headers[header_to_check] == expected_header_value
    assert session_headers[invariant_header_name] == invariant_header_value


def test_headers_unclobbered_update_with_no_provided_headers(no_fields):

    options_arg = {}  # a dict with "headers" not set

    # GIVEN:the headers and the expected value
    invariant_header_name: str = "X-Atlassian-Token"
    invariant_header_value: str = jira.client.JIRA.DEFAULT_OPTIONS["headers"][
        invariant_header_name
    ]

    # WHEN: we initialise the JIRA class with no provided headers and get the headers
    jira_client = jira.client.JIRA(
        server="https://jira.atlasian.com",
        get_server_info=False,
        validate=False,
        options=options_arg,
    )

    session_headers = jira_client._session.headers

    # THEN: we have not affected the other headers' defaults
    assert session_headers[invariant_header_name] == invariant_header_value


def test_token_auth(cl_admin: jira.client.JIRA):
    """Tests the Personal Access Token authentication works."""
    # GIVEN: We have a PAT token created by a user.
    pat_token_request = {
        "name": "my_new_token",
        "expirationDuration": 1,
    }
    base_url = cl_admin.server_url
    pat_token_response = cl_admin._session.post(
        f"{base_url}/rest/pat/latest/tokens", json=pat_token_request
    ).json()
    new_token = pat_token_response["rawToken"]

    # WHEN: A new client is authenticated with this token
    new_jira_client = jira.client.JIRA(token_auth=new_token)

    # THEN: The reported authenticated user of the token
    # matches the original token creator user.
    assert cl_admin.myself() == new_jira_client.myself()


def test_cookie_auth(test_manager: JiraTestManager):
    """Test Cookie based authentication works.

    NOTE: this is deprecated in Cloud and is not recommended in Server.
    https://developer.atlassian.com/cloud/jira/platform/jira-rest-api-cookie-based-authentication/
    https://developer.atlassian.com/server/jira/platform/cookie-based-authentication/
    """
    # GIVEN: the username and password
    # WHEN: We create a session with cookie auth for the same server
    cookie_auth_jira = jira.client.JIRA(
        server=test_manager.CI_JIRA_URL,
        auth=(test_manager.CI_JIRA_ADMIN, test_manager.CI_JIRA_ADMIN_PASSWORD),
    )
    # THEN: We get the same result from the API
    assert test_manager.jira_admin.myself() == cookie_auth_jira.myself()
