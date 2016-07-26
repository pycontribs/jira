import pytest
from tests import find_by_id
from tests import rndstr


@pytest.fixture
def td(test_manager):
    return {
        'project_b': test_manager.project_b,
        'project_b_issue1': test_manager.project_b_issue1
    }


def test_projects(jira_admin):
    projects = jira_admin.projects()
    assert len(projects) >= 2


def test_project(jira_admin, td):
    project = jira_admin.project(td['project_b'])
    assert project.key == td['project_b']


def test_set_project_avatar(jira_admin, td):
    def find_selected_avatar(avatars):
        for avatar in avatars['system']:
            if avatar['isSelected']:
                return avatar
        else:
            raise Exception

    jira_admin.set_project_avatar(td['project_b'], '10001')
    avatars = jira_admin.project_avatars(td['project_b'])
    assert find_selected_avatar(avatars)['id'] == '10001'

    project = jira_admin.project(td['project_b'])
    jira_admin.set_project_avatar(project, '10208')
    avatars = jira_admin.project_avatars(project)
    assert find_selected_avatar(avatars)['id'] == '10208'


def test_project_components(jira_admin, td):
    proj = jira_admin.project(td['project_b'])
    name = "component-%s from project %s" % (proj, rndstr())
    component = jira_admin.create_component(
        name,
        proj,
        description='test!!',
        assigneeType='COMPONENT_LEAD',
        isAssigneeTypeValid=False)
    components = jira_admin.project_components(td['project_b'])
    assert len(components) == 1

    sample = find_by_id(components, component.id)
    assert sample.id == component.id
    assert sample.name == name

    component.delete()


def test_project_versions(jira_admin, td):
    name = "version-%s" % rndstr()
    version = jira_admin.create_version(
        name, td['project_b'], "will be deleted soon")
    versions = jira_admin.project_versions(td['project_b'])

    assert len(versions) >= 1

    test = find_by_id(versions, version.id)
    assert test.id == version.id
    assert test.name == name

    i = jira_admin.issue(td['project_b_issue1'])
    i.update(fields={
        'versions': [{'id': version.id}],
        'fixVersions': [{'id': version.id}]})

    version.delete()


def test_project_versions_with_project_obj(jira_admin, td):
    name = "version-%s" % rndstr()
    version = jira_admin.create_version(
        name, td['project_b'], "will be deleted soon")
    project = jira_admin.project(td['project_b'])
    versions = jira_admin.project_versions(project)

    assert len(versions) >= 1

    test = find_by_id(versions, version.id)
    assert test.id == version.id
    assert test.name == name

    version.delete()


@pytest.mark.skipif(True,
                    reason="temporary disabled because roles() return"
                    "a dictionary of role_name:role_url and we have no "
                    "call to convert it to proper Role()")
def test_project_roles(jira_admin, td):
    project = jira_admin.project(td['project_b'])
    role_name = 'Developers'
    dev = None
    our_roles = [
        jira_admin.project_roles(td['project_b']),
        jira_admin.project_roles(project)
    ]
    for roles in our_roles:
        assert len(roles) >= 5
        assert 'Users' in roles
        assert role_name in roles
        dev = roles[role_name]

    assert dev

    role = jira_admin.project_role(td['project_b'], dev.id)
    assert role.id == dev.id
    assert role.name == dev.name

    user = jira_admin
    assert user not in role.actors

    role.update(users=user, groups=['jira-developers', 'jira-users'])
    role = jira_admin.project_role(td['project_b'], dev.id)
    assert user in role.actors

# I have no idea what avatars['custom'] is and I get different results every time
#    def test_project_avatars(jira_admin):
#        avatars = jira_admin.project_avatars(td['project_b'])
#        self.assertEqual(len(avatars['custom']), 3)
#        self.assertEqual(len(avatars['system']), 16)
#
#    def test_project_avatars_with_project_obj(jira_admin):
#        project = jira_admin.project(td['project_b'])
#        avatars = jira_admin.project_avatars(project)
#        self.assertEqual(len(avatars['custom']), 3)
#        self.assertEqual(len(avatars['system']), 16)

#    def test_create_project_avatar(jira_admin):
# Tests the end-to-end project avatar creation process: upload as temporary, confirm after cropping,
# and selection.
#        project = jira_admin.project(td['project_b'])
#        size = os.path.getsize(TEST_ICON_PATH)
#        filename = os.path.basename(TEST_ICON_PATH)
#        with open(TEST_ICON_PATH, "rb") as icon:
#            props = jira_admin.create_temp_project_avatar(project, filename, size, icon.read())
#        self.assertIn('cropperOffsetX', props)
#        self.assertIn('cropperOffsetY', props)
#        self.assertIn('cropperWidth', props)
#        self.assertTrue(props['needsCropping'])
#
#        props['needsCropping'] = False
#        avatar_props = jira_admin.confirm_project_avatar(project, props)
#        self.assertIn('id', avatar_props)
#
#        jira_admin.set_project_avatar(td['project_b'], avatar_props['id'])
#
#    def test_delete_project_avatar(jira_admin):
#        size = os.path.getsize(TEST_ICON_PATH)
#        filename = os.path.basename(TEST_ICON_PATH)
#        with open(TEST_ICON_PATH, "rb") as icon:
#            props = jira_admin.create_temp_project_avatar(td['project_b'], filename, size, icon.read(), auto_confirm=True)
#        jira_admin.delete_project_avatar(td['project_b'], props['id'])
#
#    def test_delete_project_avatar_with_project_obj(jira_admin):
#        project = jira_admin.project(td['project_b'])
#        size = os.path.getsize(TEST_ICON_PATH)
#        filename = os.path.basename(TEST_ICON_PATH)
#        with open(TEST_ICON_PATH, "rb") as icon:
#            props = jira_admin.create_temp_project_avatar(project, filename, size, icon.read(), auto_confirm=True)
#        jira_admin.delete_project_avatar(project, props['id'])
