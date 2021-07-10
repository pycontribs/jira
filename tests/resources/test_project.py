from tests.conftest import JiraTestCase, find_by_id, rndstr


class ProjectTests(JiraTestCase):
    def test_projects(self):
        projects = self.jira.projects()
        self.assertGreaterEqual(len(projects), 2)

    def test_project(self):
        project = self.jira.project(self.project_b)
        self.assertEqual(project.key, self.project_b)

    def test_project_expand(self):
        project = self.jira.project(self.project_b)
        self.assertFalse(hasattr(project, "projectKeys"))
        project = self.jira.project(self.project_b, expand="projectKeys")
        self.assertTrue(hasattr(project, "projectKeys"))

    def test_projects_expand(self):
        projects = self.jira.projects()
        for project in projects:
            self.assertFalse(hasattr(project, "projectKeys"))
        projects = self.jira.projects(expand="projectKeys")
        for project in projects:
            self.assertTrue(hasattr(project, "projectKeys"))

    # I have no idea what avatars['custom'] is and I get different results every time
    #    def test_project_avatars(self):
    #        avatars = self.jira.project_avatars(self.project_b)
    #        self.assertEqual(len(avatars['custom']), 3)
    #        self.assertEqual(len(avatars['system']), 16)
    #
    #    def test_project_avatars_with_project_obj(self):
    #        project = self.jira.project(self.project_b)
    #        avatars = self.jira.project_avatars(project)
    #        self.assertEqual(len(avatars['custom']), 3)
    #        self.assertEqual(len(avatars['system']), 16)

    #    def test_create_project_avatar(self):
    # Tests the end-to-end project avatar creation process: upload as temporary, confirm after cropping,
    # and selection.
    #        project = self.jira.project(self.project_b)
    #        size = os.path.getsize(TEST_ICON_PATH)
    #        filename = os.path.basename(TEST_ICON_PATH)
    #        with open(TEST_ICON_PATH, "rb") as icon:
    #            props = self.jira.create_temp_project_avatar(project, filename, size, icon.read())
    #        self.assertIn('cropperOffsetX', props)
    #        self.assertIn('cropperOffsetY', props)
    #        self.assertIn('cropperWidth', props)
    #        self.assertTrue(props['needsCropping'])
    #
    #        props['needsCropping'] = False
    #        avatar_props = self.jira.confirm_project_avatar(project, props)
    #        self.assertIn('id', avatar_props)
    #
    #        self.jira.set_project_avatar(self.project_b, avatar_props['id'])
    #
    #    def test_delete_project_avatar(self):
    #        size = os.path.getsize(TEST_ICON_PATH)
    #        filename = os.path.basename(TEST_ICON_PATH)
    #        with open(TEST_ICON_PATH, "rb") as icon:
    #            props = self.jira.create_temp_project_avatar(self.project_b, filename, size, icon.read(), auto_confirm=True)
    #        self.jira.delete_project_avatar(self.project_b, props['id'])
    #
    #    def test_delete_project_avatar_with_project_obj(self):
    #        project = self.jira.project(self.project_b)
    #        size = os.path.getsize(TEST_ICON_PATH)
    #        filename = os.path.basename(TEST_ICON_PATH)
    #        with open(TEST_ICON_PATH, "rb") as icon:
    #            props = self.jira.create_temp_project_avatar(project, filename, size, icon.read(), auto_confirm=True)
    #        self.jira.delete_project_avatar(project, props['id'])

    # @pytest.mark.xfail(reason="Jira may return 500")
    # def test_set_project_avatar(self):
    #     def find_selected_avatar(avatars):
    #         for avatar in avatars['system']:
    #             if avatar['isSelected']:
    #                 return avatar
    #         else:
    #             raise Exception
    #
    #     self.jira.set_project_avatar(self.project_b, '10001')
    #     avatars = self.jira.project_avatars(self.project_b)
    #     self.assertEqual(find_selected_avatar(avatars)['id'], '10001')
    #
    #     project = self.jira.project(self.project_b)
    #     self.jira.set_project_avatar(project, '10208')
    #     avatars = self.jira.project_avatars(project)
    #     self.assertEqual(find_selected_avatar(avatars)['id'], '10208')

    def test_project_components(self):
        proj = self.jira.project(self.project_b)
        name = "component-%s from project %s" % (proj, rndstr())
        component = self.jira.create_component(
            name,
            proj,
            description="test!!",
            assigneeType="COMPONENT_LEAD",
            isAssigneeTypeValid=False,
        )
        components = self.jira.project_components(self.project_b)
        self.assertGreaterEqual(len(components), 1)
        sample = find_by_id(components, component.id)
        self.assertEqual(sample.id, component.id)
        self.assertEqual(sample.name, name)
        component.delete()

    def test_project_versions(self):
        name = "version-%s" % rndstr()
        version = self.jira.create_version(name, self.project_b, "will be deleted soon")
        versions = self.jira.project_versions(self.project_b)
        self.assertGreaterEqual(len(versions), 1)
        test = find_by_id(versions, version.id)
        self.assertEqual(test.id, version.id)
        self.assertEqual(test.name, name)

        i = self.jira.issue(self.test_manager.project_b_issue1)
        i.update(fields={"fixVersions": [{"id": version.id}]})
        version.delete()

    def test_update_project_version(self):
        # given
        name = "version-%s" % rndstr()
        version = self.jira.create_version(name, self.project_b, "will be deleted soon")
        updated_name = "version-%s" % rndstr()
        # when
        version.update(name=updated_name)
        # then
        self.assertEqual(updated_name, version.name)
        version.delete()

    def test_get_project_version_by_name(self):
        name = "version-%s" % rndstr()
        version = self.jira.create_version(name, self.project_b, "will be deleted soon")

        found_version = self.jira.get_project_version_by_name(self.project_b, name)
        self.assertEqual(found_version.id, version.id)
        self.assertEqual(found_version.name, name)

        not_found_version = self.jira.get_project_version_by_name(
            self.project_b, "non-existent"
        )
        self.assertEqual(not_found_version, None)

        i = self.jira.issue(self.test_manager.project_b_issue1)
        i.update(fields={"fixVersions": [{"id": version.id}]})
        version.delete()

    def test_rename_version(self):
        old_name = "version-%s" % rndstr()
        version = self.jira.create_version(
            old_name, self.project_b, "will be deleted soon"
        )

        new_name = old_name + "-renamed"
        self.jira.rename_version(self.project_b, old_name, new_name)

        found_version = self.jira.get_project_version_by_name(self.project_b, new_name)
        self.assertEqual(found_version.id, version.id)
        self.assertEqual(found_version.name, new_name)

        not_found_version = self.jira.get_project_version_by_name(
            self.project_b, old_name
        )
        self.assertEqual(not_found_version, None)

        i = self.jira.issue(self.test_manager.project_b_issue1)
        i.update(fields={"fixVersions": [{"id": version.id}]})
        version.delete()

    def test_project_versions_with_project_obj(self):
        name = "version-%s" % rndstr()
        version = self.jira.create_version(name, self.project_b, "will be deleted soon")
        project = self.jira.project(self.project_b)
        versions = self.jira.project_versions(project)
        self.assertGreaterEqual(len(versions), 1)
        test = find_by_id(versions, version.id)
        self.assertEqual(test.id, version.id)
        self.assertEqual(test.name, name)
        version.delete()

    def test_project_roles(self):
        role_name = "Administrators"
        admin = None
        roles = self.jira.project_roles(self.project_b)
        self.assertGreaterEqual(len(roles), 1)
        self.assertIn(role_name, roles)
        admin = roles[role_name]
        self.assertTrue(admin)
        role = self.jira.project_role(self.project_b, admin["id"])
        self.assertEqual(role.id, int(admin["id"]))

        actornames = {actor.name: actor for actor in role.actors}
        actor_admin = "jira-administrators"
        self.assertIn(actor_admin, actornames)
        members = self.jira.group_members(actor_admin)
        user = self.user_admin
        self.assertIn(user.name, members.keys())
        role.update(users=user.name, groups=actor_admin)
        role = self.jira.project_role(self.project_b, int(admin["id"]))
        self.assertIn(user.name, [a.name for a in role.actors])
        self.assertIn(actor_admin, [a.name for a in role.actors])
