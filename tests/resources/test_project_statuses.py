from tests.conftest import JiraTestCase


class ProjectStatusesTests(JiraTestCase):
    def test_project_statuses(self):
        project_statuses = self.jira.project_statuses(self.project_a)

        # project should have at least one status
        self.assertGreater(len(project_statuses), 0)

        # first project status
        project_status = project_statuses[0]
        # test statues id
        self_status_id = self.jira.status(project_status.id).id
        self.assertEqual(self_status_id, project_status.id)
        # test statues name 
        self_status_name = self.jira.status(project_status.name).name
        self.assertEqual(self_status_name, project_status.name)
